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
    VERSION = "0.3.3"
    AUTHOR = "Jackymancs4"
    LICENSE = "MIT"
    ACTION_NAME = "amazon"

    def get_filenames(self, path_to_zip):
        """return list of filenames inside of the zip folder"""
        with ZipFile(path_to_zip, "r") as zip:
            return zip.namelist()

    def validate_date(self, date_string):
        date = None

        try:
            date = datetime.fromisoformat(date_string)
        except:
            print('Invalid date: ' + date_string)

        return date

    def get_part_name(self, part_name):
        return (part_name[:50] + "..") if len(part_name) > 50 else part_name

    def get_part_description(self, part_name):
        return part_name if len(part_name) > 50 else ""

    def process_order(self, order_data, supplier):

            order_id = order_data[1]
            order_date = self.validate_date(order_data[2])
            order_issue_date = order_date
            order_completed_date = self.validate_date(order_data[18])

            part_name = self.get_part_name(order_data[23])
            part_description = self.get_part_description(order_data[23])

            part_code = order_data[12]

            part_quantity = order_data[14]
            part_total_price = order_data[9]
            part_price_currency = order_data[4]

            order = PurchaseOrder.objects.filter(supplier=supplier, supplier_reference=order_id).first()

            if not order:
                print("Order not found by reference: " + order_id)

                order = PurchaseOrder.objects.get_or_create(
                    supplier=supplier,
                    supplier_reference=order_id,
                )[0]

                order.creation_date=order_date,
                order.issue_date=order_issue_date,
                order.complete_date=order_completed_date,

                order.save()

            supplier_part = SupplierPart.objects.filter(supplier=supplier, SKU=part_code).first()

            if not supplier_part: 

                part = Part.objects.get_or_create(
                    name=part_name,
                    description=part_description,
                )[0]

                supplier_part = SupplierPart.objects.get_or_create(
                    part=part, supplier=supplier, SKU=part_code
                )[0]

                supplier_part.link = "https://" + order_data[0] + "/dp/" + part_code
                supplier_part.save()

            else:
                part = supplier_part.part

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

            return order

    def process_order_history(self, data, supplier):

        print("Initiate import 3")

        order_map = {}

        line_count = 0
        processed_line_count = 0

        for row in data:

            # Skip header line
            if line_count == 0:
                line_count += 1
                continue

            #try:

            order = self.process_order(row, supplier)
            order_map[order.pk] = order
            processed_line_count += 1
            print("Successful import: " + row[1])

            # except:
            #    print("Error import: " + row[1])
            
            line_count += 1

        print(f"Processed {line_count} lines.")

        return order_map

    def place_orders(self, data, user, default_location=None):

        line_count = 0

        for order_id in data:

            order_issue_date = data[order_id].issue_date

            data[order_id].place_order()

            data[order_id].issue_date=order_issue_date,
            data[order_id].save()

            pending_lines = data[order_id].pending_line_items()

            for pending_line in pending_lines:
                data[order_id].receive_line_item(
                    pending_line, default_location, pending_line.quantity, user
                )

        print(f"Processed {line_count} lines.")
        line_count += 1

    def complete_orders(self, data, user, default_location=None):

        line_count = 0
        for order_id in data:

            order_complete_date = data[order_id].complete_date
            data[order_id].complete_order()

            data[order_id].complete_date=order_complete_date,
            data[order_id].save()

        print(f"Processed {line_count} lines.")
        line_count += 1

    def perform_action(self, user=None, data=None):

        command = data.get("command")

        if command == "import_base64":

            zip_temp_file = NamedTemporaryFile(delete=True)

            zip_temp_file_map = {}

            zip_temp_file.write(base64.b64decode(data["content"]))

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
