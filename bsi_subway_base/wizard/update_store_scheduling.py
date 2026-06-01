# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import io,binascii,tempfile
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime, time
from datetime import datetime , date

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


class UpdateStoreScheduling(models.TransientModel):
    _name = "bsi.update.store.scheduling.wizard"
    _description = "Update Store Scheduling"

    #MP - TODO - need to test this feature (Wizard) acording to new workflow
    file = fields.Binary('File',required=True)
    # start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    store_id = fields.Many2one('store.store' , string ="Store")

    def update_store_scheduling(self):
        data_dict ={}
        try:
            xlsfile = tempfile.NamedTemporaryFile(delete= False,suffix=".xlsx")
            xlsfile.write(binascii.a2b_base64(self.file))
            xlsfile.seek(0)
            workbook = xlrd.open_workbook(xlsfile.name)
            sheet = workbook.sheet_by_index(0)
        except Exception:
            raise ValidationError(_("Please give Excel File to Import Payments/Reciepts."))

        base_row = []
        for row_no in range(sheet.nrows):

            #RM - NOV26 - store scheduling data update start
            net_sales = 0.0
            food_cost_in_percentage = 0.0
            food_cost = 0.0
            payroll_taxes = 0.0
            paychex_total_debit = 0.0
            ytd_avg_net_sales = 0.0
            allowed_percentage_food_cost = 0.0
            allowed_food_cost = 0.0
            over_or_short_food_cost = 0.0
            ytd_over_or_short_food_cost = 0.0
            #RM - NOV26 - store scheduling data update code end


            total_hours = 0.0
            fixed_hours = 0.0
            matrix_allowed_hours = 0.0
            over_or_short_matrix_hours = 0.0
            ytd_over_or_short_in_hours = 0.0
            ytd_over_or_short_dollar_in_lc = 0.0
            ytd_over_or_short_dollar_in_fc_and_lc = 0.0
            ytd_total_hours = 0.0
            per_hours_gain_or_loss = 0.0
            ytd_average_food_cost = 0.0
            average_hourly_pay = 0.0
            tips_per_employee_hour = 0.0
            total_hourly_pay_including_tips = 0.0
            ytd_average_hourly_pay = 0.0
            over_or_short_food_bank_and_truck = 0.0
            ytd_over_or_short_dollar = 0.0
            total_tips = 0.0
            ytd_average_food_cost_percentage = 0.00
            percentage_of_payroll = 0.00
            ytd_average_percentage_of_payroll = 0.00
            fc_and_lc_percentage = 0.00
            ytd_fc_and_lc_percentage = 0.00
            paid_outs = 0.00

            #RM - NOV26 - store scheduling data update start
            c_count = 0
            if row_no == 0:
                base_row = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
            if row_no > 0 and row_no < 2:
                line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                col_count = 0
                sub_line_count = 0
                end_date = self.end_date
                for rec in line:
                    if line[col_count]:
                        end_date = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(float(line[col_count])) - 2)
                        start_date = end_date - timedelta(days=6)
                        sub_rows = row_no + 1
                        while sub_rows <= 13:
                            sub_line_data  = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(sub_rows)))
                            for rec in sub_line_data:
                                if sub_line_count <= col_count :
                                    if sub_line_data[sub_line_count]== 'Net/Royalty Sales':
                                        net_sales = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Food Cost Bank':
                                        food_cost = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Food Cost %':
                                        food_cost_in_percentage = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Paychex Employer Taxes':
                                        payroll_taxes = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Paychex Total Debit':
                                        paychex_total_debit = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Avg. Sales':
                                        ytd_avg_net_sales = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Allowed % Food Cost':
                                        allowed_percentage_food_cost = 27
                                    elif sub_line_data[sub_line_count]== 'Allowed $ Food Cost':
                                        allowed_food_cost = sub_line_data[col_count]
                                    # elif sub_line_data[sub_line_count]== 'Truck Order #1 $ Subventory':
                                    #     sales_data = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Over or Short $':
                                        over_or_short_food_cost = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Over or Short $ in FC':
                                        ytd_over_or_short_food_cost = sub_line_data[col_count]
                            
                            sub_rows += 1
                            c_count = c_count + 1
                        bsi_store_id = self.env['store.scheduling'].search([('week_starting_date', '=', start_date.date()), ('store_id', '=', self.store_id.id)])
                        if bsi_store_id:
                            vals = {
                                'store_id': self.store_id.id,
                                'week_starting_date': start_date,
                                'week_ending_date': end_date,
                                'net_sales':net_sales,
                                'food_cost_in_percentage':food_cost_in_percentage,
                                'food_cost':food_cost,
                                'payroll_taxes':payroll_taxes,
                                'paychex_total_debit':paychex_total_debit,
                                # 'ytd_avg_net_sales':ytd_avg_net_sales,
                                'allowed_percentage_food_cost':allowed_percentage_food_cost,
                                'allowed_food_cost':allowed_food_cost,
                                'over_or_short_food_cost':over_or_short_food_cost,
                                'ytd_over_or_short_food_cost':ytd_over_or_short_food_cost,
                                'state' :'done',
                            }
                            bsi_store_id.update(vals)

                        else:
                            create_vals = {
                                'store_id': self.store_id.id,
                                'week_starting_date': start_date,
                                'week_ending_date': end_date,
                                'net_sales':net_sales,
                                'food_cost_in_percentage':food_cost_in_percentage,
                                'food_cost':food_cost,
                                'payroll_taxes':payroll_taxes,
                                'paychex_total_debit':paychex_total_debit,
                                # 'ytd_avg_net_sales':ytd_avg_net_sales,
                                'allowed_percentage_food_cost':allowed_percentage_food_cost,
                                'allowed_food_cost':allowed_food_cost,
                                'over_or_short_food_cost':over_or_short_food_cost,
                                'ytd_over_or_short_food_cost':ytd_over_or_short_food_cost,
                                'state' :'done',
                            }
                            bsi_store_id = self.env['store.scheduling'].create(create_vals)

                    col_count += 1
            #RM - NOV26 - store scheduling data update code end

            if row_no == 0:
                base_row = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
            if row_no == 1 :
                line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                col_count = 0
                sub_line_count = 0
                end_date = self.end_date
                start_row = 78

                for rec in line:
                    if line[col_count] :

                        end_date = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(float(line[col_count])) - 2)
                        start_date = end_date - timedelta(days=6)

                        sub_rows = start_row + 1
                        while sub_rows <= sheet.nrows - 1 :
                            sub_line_data  = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(sub_rows)))
                            for rec in sub_line_data:
                                if sub_line_count <= col_count :
                                    if sub_line_data[sub_line_count]== 'Total Hours':
                                        total_hours = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'FIXED Hours':
                                        fixed_hours = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Matrix Allowed Hours':
                                        matrix_allowed_hours = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Over or Short Matrix Hours':
                                        over_or_short_matrix_hours = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Over or Short in Hours':
                                        ytd_over_or_short_in_hours = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Over or Short $ in LC':
                                        ytd_over_or_short_dollar_in_lc = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Over or Short $ in FC and LC':
                                        ytd_over_or_short_dollar_in_fc_and_lc = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Total Hours':
                                        ytd_total_hours = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Per Hours Gain or Loss':
                                        per_hours_gain_or_loss = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Average Food Cost':
                                        ytd_average_food_cost = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Average Hourly Pay':
                                        average_hourly_pay = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'TIPS PER EMPLOYEE HOUR':
                                        tips_per_employee_hour = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Total Hourly Pay Including Tips':
                                        total_hourly_pay_including_tips = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Average Hourly Pay':
                                        ytd_average_hourly_pay = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'Overor Short $ Bank Vs Truck Order #1':
                                        over_or_short_food_bank_and_truck = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Over or Short $':
                                        ytd_over_or_short_dollar = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'TOTAL TIPS':
                                        total_tips = sub_line_data[col_count]
                                    elif sub_line_data[sub_line_count]== 'YTD Avg Food Cost %':
                                        if sub_line_data[col_count]:
                                            ytd_average_food_cost_percentage = float(sub_line_data[col_count]) * 100
                                        else:
                                            ytd_average_food_cost_percentage = 0.00
                                    elif sub_line_data[sub_line_count]== '% of Payroll':
                                        if sub_line_data[col_count]:
                                            percentage_of_payroll = float(sub_line_data[col_count]) * 100
                                        else:
                                            percentage_of_payroll = 0.00
                                    elif sub_line_data[sub_line_count]== 'YTD Avg % of Payroll':
                                        if sub_line_data[col_count]:
                                            ytd_average_percentage_of_payroll = float(sub_line_data[col_count]) * 100
                                        else:
                                            ytd_average_percentage_of_payroll = 0.00
                                    elif sub_line_data[sub_line_count]== 'FC & LC %':
                                        if sub_line_data[col_count]:
                                            fc_and_lc_percentage = float(sub_line_data[col_count]) * 100
                                        else:
                                            fc_and_lc_percentage = 0.00
                                    elif sub_line_data[sub_line_count]== 'YTD FC & LC %':
                                        if sub_line_data[col_count]:
                                            ytd_fc_and_lc_percentage = float(sub_line_data[col_count]) * 100
                                        else:
                                            ytd_fc_and_lc_percentage = 0.00
                                    elif sub_line_data[sub_line_count]== 'PAID OUTS':
                                        if sub_line_data[col_count]:
                                            paid_outs = float(sub_line_data[col_count])
                                        else:
                                            paid_outs = 0.00

                            sub_rows += 1
                        bsi_store_id = self.env['store.scheduling'].search([('week_starting_date', '=', start_date.date()), ('store_id', '=', self.store_id.id)])
                        if bsi_store_id:
                            vals = {
                                'total_hours': total_hours,
                                'fixed_hours': fixed_hours,
                                'matrix_allowed_hours': matrix_allowed_hours,
                                'over_or_short_matrix_hours':over_or_short_matrix_hours,
                                'ytd_over_or_short_in_hours':ytd_over_or_short_in_hours,
                                'ytd_over_or_short_dollar_in_lc':ytd_over_or_short_dollar_in_lc,
                                'ytd_over_or_short_dollar_in_fc_and_lc':ytd_over_or_short_dollar_in_fc_and_lc,
                                'ytd_total_hours':ytd_total_hours,
                                'per_hours_gain_or_loss':per_hours_gain_or_loss,
                                'ytd_average_food_cost':ytd_average_food_cost,
                                'average_hourly_pay':average_hourly_pay,
                                'tips_per_employee_hour':tips_per_employee_hour,
                                'total_hourly_pay_including_tips':total_hourly_pay_including_tips,
                                'ytd_average_hourly_pay' :ytd_average_hourly_pay,
                                'over_or_short_food_bank_and_truck': over_or_short_food_bank_and_truck,
                                'ytd_over_or_short_dollar': ytd_over_or_short_dollar,
                                'total_tips': total_tips,
                                'ytd_average_food_cost_percentage': ytd_average_food_cost_percentage,
                                'percentage_of_payroll': percentage_of_payroll,
                                'ytd_average_percentage_of_payroll': ytd_average_percentage_of_payroll,
                                'fc_and_lc_percentage': fc_and_lc_percentage,
                                'ytd_fc_and_lc_percentage': ytd_fc_and_lc_percentage,
                                'paid_outs': paid_outs,
                            }
                            bsi_store_id.update(vals)
                        # bsi_store_id = self.env['store.scheduling'].create(vals)
                        # bsi_store_id._compute_ytd_avg_net_sales()
                        # start_row += 1

                    col_count += 1
