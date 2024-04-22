"""Sample implementation for ActionMixin."""

import inspect, json, logging

from plugin import InvenTreePlugin
from plugin.mixins import ActionMixin, APICallMixin, SettingsMixin, EventMixin
from company.models import Company, SupplierPriceBreak
from part.models import Part, SupplierPart, PartCategory, PartParameterTemplate, PartParameter
from stock.models import StockItem

logger = logging.getLogger("spoolmanplugin")

class SpoolmanPlugin(ActionMixin, APICallMixin, SettingsMixin, InvenTreePlugin):
    """An action plugin which offers variuous integrations with Spoolman."""

    NAME = 'SpoolmanPlugin'
    SLUG = 'spoolman'
    ACTION_NAME = 'spoolman'

    SETTINGS = {
        'API_URL': {
            'name': 'External URL',
            'description': 'Where is your API located?',
            "required": True,
        },
        'FILAMENT_CATEGORY_ID': {
            'name': 'Category for filament parts',
            'description': 'Where is your API located?',
            "model": "part.partcategory",
        },
        'MATERIAL_PART_PARAMETER_ID': {
            'name': 'Material Part Parameter',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
        'DENSITY_PART_PARAMETER_ID': {
            'name': 'Density Part Parameter',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
        'DIAMETER_PART_PARAMETER_ID': {
            'name': 'External URL',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
        'SPOOL_WEIGHT_PART_PARAMETER_ID': {
            'name': 'External URL',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
        'MIN_EXTRUDER_TEMP_PART_PARAMETER_ID': {
            'name': 'External URL',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
        'MAX_EXTRUDER_TEMP_PART_PARAMETER_ID': {
            'name': 'External URL',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
        'MIN_BED_TEMP_PART_PARAMETER_ID': {
            'name': 'External URL',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
        'MAX_BED_TEMP_PART_PARAMETER_ID': {
            'name': 'External URL',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
        'COLOR_PART_PARAMETER_ID': {
            'name': 'External URL',
            'description': 'Where is your API located?',
            "model": "part.partparametertemplate",
        },
    }

    API_URL_SETTING = 'API_URL'

    result = {}

    @property
    def api_url(self):
        """Base url path."""
        return f'{self.get_setting(self.API_URL_SETTING)}'

    def create_part_parameters(self):
        """Add all the part parameters not already set through the settings"""

        parameter_template_pk = False
        parameter_template = None

        parameter_template_pk = self.get_setting("MATERIAL_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Material")[0]
            self.set_setting("MATERIAL_PART_PARAMETER_ID", parameter_template.pk)

        parameter_template_pk = self.get_setting("DENSITY_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Density", units="gram / centimeter ** 3")[0]
            self.set_setting("DENSITY_PART_PARAMETER_ID", parameter_template.pk)

        parameter_template_pk = self.get_setting("DIAMETER_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Diameter", units="mm")[0]
            self.set_setting("DIAMETER_PART_PARAMETER_ID", parameter_template.pk)

        parameter_template_pk = self.get_setting("SPOOL_WEIGHT_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Spool Weight", units="g")[0]
            self.set_setting("SPOOL_WEIGHT_PART_PARAMETER_ID", parameter_template.pk)

        parameter_template_pk = self.get_setting("MIN_EXTRUDER_TEMP_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Min Ext temp", units="degC")[0]
            self.set_setting("MIN_EXTRUDER_TEMP_PART_PARAMETER_ID", parameter_template.pk)

        parameter_template_pk = self.get_setting("MAX_EXTRUDER_TEMP_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Max Ext temp", units="degC")[0]
            self.set_setting("MAX_EXTRUDER_TEMP_PART_PARAMETER_ID", parameter_template.pk)

        parameter_template_pk = self.get_setting("MIN_BED_TEMP_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Min Bed temp", units="degC")[0]
            self.set_setting("MIN_BED_TEMP_PART_PARAMETER_ID", parameter_template.pk)

        parameter_template_pk = self.get_setting("MAX_BED_TEMP_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Max Bed temp", units="degC")[0]
            self.set_setting("MAX_BED_TEMP_PART_PARAMETER_ID", parameter_template.pk)

        parameter_template_pk = self.get_setting("COLOR_PART_PARAMETER_ID")

        if not parameter_template_pk:
            parameter_template = PartParameterTemplate.objects.get_or_create(name="Hex Color")[0]
            self.set_setting("COLOR_PART_PARAMETER_ID", parameter_template.pk)

    def process_spool(self, spool, category):

            supplier_name = None
            supplier = None

            # ottieni il supplier
            if "vendor" in spool["filament"]: 
                supplier_name = spool["filament"]["vendor"]["name"]
                supplier=Company.objects.get_or_create(
                    name=supplier_name,
                )[0]

                supplier.notes = spool["filament"]["vendor"]["comment"] if "comment" in spool["filament"]["vendor"] else ""

                supplier.save()

            # se non presente lo crei

            # ottieni il filamento
            if supplier_name: 
                part_name = supplier_name + " " + spool["filament"]["name"]
            else:
                part_name = spool["filament"]["name"]

            part = Part.objects.filter(metadata__contains=[{'spoolman_id': spool["filament"]["id"]}]).first()

            if not part:
                print("Filament not found by ID")

                part=Part.objects.get_or_create(
                    name=part_name, 
                    category=category,
                )[0]

            part.metadata["spoolman_id"] = spool["filament"]["id"]

            part.notes = spool["filament"]["comment"] if "comment" in spool["filament"] else ""
            part.units = "g"
            part.component = True

            part.save()

            parameter_template_pk = self.get_setting("MATERIAL_PART_PARAMETER_ID")

            if "material" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["material"]
                )[0]

            parameter_template_pk = self.get_setting("DENSITY_PART_PARAMETER_ID")

            if "density" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["density"]
                )[0]

            parameter_template_pk = self.get_setting("DIAMETER_PART_PARAMETER_ID")

            if "diameter" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["diameter"]
                )[0]

            parameter_template_pk = self.get_setting("SPOOL_WEIGHT_PART_PARAMETER_ID")

            if "spool_weight" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["spool_weight"]
                )[0]

            parameter_template_pk = self.get_setting("MIN_EXTRUDER_TEMP_PART_PARAMETER_ID")

            if "settings_extruder_temp" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["settings_extruder_temp"]
                )[0]

            parameter_template_pk = self.get_setting("MAX_EXTRUDER_TEMP_PART_PARAMETER_ID")

            if "settings_extruder_temp" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["settings_extruder_temp"]
                )[0]

            parameter_template_pk = self.get_setting("MIN_BED_TEMP_PART_PARAMETER_ID")

            if "settings_bed_temp" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["settings_bed_temp"]
                )[0]

            parameter_template_pk = self.get_setting("MAX_BED_TEMP_PART_PARAMETER_ID")

            if "settings_bed_temp" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["settings_bed_temp"]
                )[0]

            parameter_template_pk = self.get_setting("COLOR_PART_PARAMETER_ID")

            if "color_hex" in spool["filament"] and parameter_template_pk: 

                parameter_template = PartParameterTemplate.objects.get(pk=parameter_template_pk)

                PartParameter.objects.get_or_create(
                    part = part, 
                    template = parameter_template, 
                    data = spool["filament"]["color_hex"]
                )[0]

            # se non presente lo crei

            # colleghi il filamento al supplier
            if supplier != None:    
                supplier_part = SupplierPart.objects.get_or_create(
                    part = part, 
                    supplier = supplier,
                )[0]

                supplier_part.SKU = spool["filament"]["article_number"] if "article_number" in spool["filament"] else spool["filament"]["id"]
                supplier_part.pack_quantity = str(spool["filament"]["weight"])

                supplier_part.save()

                if "price" in spool["filament"]:

                    supplier_price_break = SupplierPriceBreak.objects.get_or_create(
                        part = supplier_part,
                        quantity = 1,
                    )[0]

                    supplier_price_break.price = str(spool["filament"]["price"])

                    supplier_price_break.save()

            # crei la giacenza
            stock = StockItem.objects.get_or_create(
                part=part, 
                batch = spool["lot_nr"]
            )[0]

            stock.updateQuantity(spool["remaining_weight"])

    def clear_metadata(self):
        parts = Part.objects.filter(metadata__icontains='spoolman_id')

        for part in parts:
            print("Spoolman part found: " + str(part.pk))

            part.metadata.pop('spoolman_id')
            part.save()

    def perform_action(self, user=None, data=None):

        initial_response = self.api_call('api/v1/info', simple_response=False)

        if initial_response.status_code != 200:
            self.result = {'error'}
            return False
        
        print(str(data))

        command = data.get('command')

        if command == 'import':

            filaments_response = self.api_call('api/v1/spool')

            category = None

            if category_pk := self.get_setting("FILAMENT_CATEGORY_ID"):
                try:
                    category = PartCategory.objects.get(pk=category_pk)
                except PartCategory.DoesNotExist:
                    category = None
                
            # Per ogni spool
            for spool in filaments_response:
                self.process_spool(spool, category)

                print("Imported spool " + str(spool["id"]))

        elif command == 'create_part_parameter_templates':
            self.create_part_parameters()

        elif command == 'clear_metadata':
            self.clear_metadata()

        else:
            self.result = {'error'}

    def get_info(self, user, data=None):
        """Sample method."""
        return {'user': user.username, 'hello': 'world'}

    def get_result(self, user=None, data=None):
        """Sample method."""
        return self.result
