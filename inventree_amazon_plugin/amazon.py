from decimal import Decimal
from plugin import InvenTreePlugin
from plugin.mixins import ActionMixin, APICallMixin, SettingsMixin, EventMixin
from part.models import (
    Part,
    SupplierPart,
    PartCategory,
    PartParameterTemplate,
    PartParameter,
    BomItem,
    BomItemSubstitute,
)
from company.models import Company
from order.models import Order, OrderLineItem, PurchaseOrder, PurchaseOrderLineItem
from datetime import datetime
from django.core.files.temp import NamedTemporaryFile
from zipfile import ZipFile
import base64
import csv


class ImportAmazonOrdersPlugin(ActionMixin, SettingsMixin, InvenTreePlugin):
    """An action plugin which allows to import Amazon orders data export into Inventree."""

    NAME = "AmazonOrdersImport"
    SLUG = "amazonordersimport"
    TITLE = "Amazon Import"
    DESCRIPTION = ("Amazon orders import for InvenTree")
    VERSION = "0.2"
    AUTHOR = "Jackymancs4"
    LICENSE = "MIT"
    ACTION_NAME = "spoolman"

    def get_filenames(self, path_to_zip):
        """return list of filenames inside of the zip folder"""
        with ZipFile(path_to_zip, "r") as zip:
            return zip.namelist()

    def process_order_history(self, data, supplier):

        order_map = {}

        line_count = 0
        for row in data:
            if line_count == 0:
                line_count += 1
                continue

            order_id = row[1]
            order_date = datetime.fromisoformat(row[2])

            part_name = (row[23][:50] + "..") if len(row[23]) > 50 else row[23]
            part_code = row[12]
            part_description = row[23] if len(row[23]) > 50 else ""
            part_quantity = row[14]
            part_total_price = row[9]
            part_price_currency = row[4]

            if order_id not in order_map:

                order = PurchaseOrder.objects.get_or_create(
                    supplier=supplier,
                    supplier_reference=order_id,
                    creation_date=order_date,
                    issue_date=order_date,
                )[0]

                order_map[order_id] = order
            else:
                order = order_map[order_id]

            supplier_part = SupplierPart.objects.filter(supplier=supplier, SKU=part_code).first()

            if not supplier_part: 

                part = Part.objects.get_or_create(
                    name=part_name,
                    description=part_description,
                )[0]

                supplier_part = SupplierPart.objects.get_or_create(
                    part=part, supplier=supplier, SKU=part_code
                )[0]

                supplier_part.link = "https://" + row[0] + "/dp/" + part_code
                supplier_part.save()

            else:
                part = Part.objects.get(pk=supplier_part.part)

            order_line_item = PurchaseOrderLineItem.objects.get_or_create(
                order=order,
                part=supplier_part,
                quantity=part_quantity,
                purchase_price_currency=part_price_currency,
            )[0]

            order_line_item.purchase_price = Decimal(part_total_price) / (
                1 if Decimal(part_quantity) == 0.0 else Decimal(part_quantity)
            )
            order_line_item.save()

        print(f"Processed {line_count} lines.")
        line_count += 1

        return order_map

    def place_orders(self, data, user, default_location=None):

        line_count = 0

        for order in data:

            data[order].place_order()

            pending_lines = data[order].pending_line_items()

            for pending_line in pending_lines:
                data[order].receive_line_item(
                    pending_line, default_location, pending_line.quantity, user
                )

        print(f"Processed {line_count} lines.")
        line_count += 1

    def complete_orders(self, data, user, default_location=None):

        line_count = 0
        for order in data:

            data[order].complete_order()

        print(f"Processed {line_count} lines.")
        line_count += 1

    def perform_action(self, user=None, data=None):

        command = data.get("command")

        if command == "import_base64":

            zip_temp_file = NamedTemporaryFile(delete=True)

            zip_temp_file_map = {}

            zip_temp_file.write(base64.b64decode(data["data"]))

            company = Company.objects.get_or_create(
                name="Amazon",
                is_supplier=True,
            )[0]

            with ZipFile(zip_temp_file.name, "r") as zip:

                for zip_file_name in zip.namelist():
                    zip_file_content = zip.read(zip_file_name)

                    zip_temp_file_map[zip_file_name] = NamedTemporaryFile(delete=True)
                    zip_temp_file_map[zip_file_name].write(zip_file_content)

                    if zip_file_name == "Retail.OrderHistory.2/Retail.OrderHistory.2.csv":

                        csv_reader = csv.reader(
                            zip_file_content.decode().splitlines(),
                            delimiter=",",
                            lineterminator="\n",
                        )

                        orders = self.process_order_history(csv_reader, company)

                        self.place_orders(orders, user)

                        self.complete_orders(orders, user)
        else:
            self.result = {"error"}
