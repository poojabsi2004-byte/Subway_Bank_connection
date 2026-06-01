# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import io,binascii,tempfile
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime, time
from datetime import datetime , date
import xlrd

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class ImportMultiStoresDataEntry(models.TransientModel):
    _name = "bsi.import.multi.stores.data.entry.wizard"
    _description = "Import Multi Stores Data Entry"

    file = fields.Binary('File',required=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    store_id = fields.Many2one('store.store' , string ="Store")

    #MP - TODO - need to test this feature (Wizard) acording to new workflow
    @staticmethod
    def convert_excel_date(excel_date, datemode):
        if isinstance(excel_date, float):
            date_tuple = xlrd.xldate_as_tuple(excel_date, datemode)
            return datetime(*date_tuple).date()
        return excel_date

    @staticmethod
    def get_create_json_values(data, store_id):
        vals = {}
        for key,value in data.items():
            if key == 'store_id':
                vals[key] = store_id.id
            else:
                vals[key] = value
        return vals

    @staticmethod
    def get_write_json_values(data,bsi_store_id):
        vals = {}
        for key,value in data.items():
            if key in ['store_id', 'week_starting_date', 'week_ending_date']:
                continue
            else:
                if value != getattr(bsi_store_id, key, ''):
                    vals[key] = value
        return vals
    
    def import_multi_stores_data_button(self):
        try:
            xlsfile = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            xlsfile.write(binascii.a2b_base64(self.file))
            xlsfile.seek(0)
            workbook = xlrd.open_workbook(xlsfile.name)
            sheet = workbook.sheet_by_index(0)

        except Exception as e:
            raise ValidationError(f"Error reading Excel file: {str(e)}")

        base_col = []
        technical_names = [sheet.cell_value(0, col) for col in range(sheet.ncols)]
        values = []
        errors = []

        for row in range(2, sheet.nrows):
            if sheet.nrows < 3:
                raise ValidationError("The Excel file must have at least 3 rows (technical, string, and data rows).")
            val = {}
            for col in range(sheet.ncols):
                val[technical_names[col]] = sheet.cell_value(row, col)
            values.append(val)

        for data in values:
            store_name = data.get('store_id', '').strip()          
            if not data.get('store_id', '').strip():
                raise ValidationError(_("please enter store name."))
            if not str(data.get('week_starting_date', '')).strip():
                raise ValidationError(_("please enter start date."))
            if not str(data.get('week_ending_date', '')).strip():
                raise ValidationError(_("please enter end date."))

            store_id = self.env['store.store'].sudo().search([
                ('name', '=', data['store_id'])
                ],limit=1)
            if not store_id:
                errors.append(data)

        if errors:
            string = []
            for error in errors:
                string.append("Row {}: Store '{}' not found in the stores list.".format(values.index(error) + 3,error.get('store_id', '').strip()))
            raise ValidationError("\n".join(string))

        else:
            for data in values:
                store_id = self.env['store.store'].sudo().search([
                ('name', '=', data['store_id'])
                ],limit=1)

                data['week_starting_date'] = self.convert_excel_date(data['week_starting_date'], workbook.datemode)
                data['week_ending_date'] = self.convert_excel_date(data['week_ending_date'], workbook.datemode)

                bsi_store_id = self.env['store.scheduling'].search([
                    ('week_starting_date', '=', data['week_starting_date']),
                    ('week_ending_date', '=', data['week_ending_date']),
                    ('store_id', '=', store_id.id)
                    ],limit=1)
                
                if bsi_store_id:
                    vals = self.get_write_json_values(data,bsi_store_id)
                    bsi_store_id.write(vals)
                else:
                    vals = self.get_create_json_values(data, store_id)
                    self.env['store.scheduling'].create(vals)
