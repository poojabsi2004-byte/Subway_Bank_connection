# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime , date
import pytz
from pytz import timezone


class EmployeePayrollEntries(models.TransientModel):
    _name = "bsi.employee.payroll.entry.wizard"
    _description = "Employee Payroll  Entries"

    store_id = fields.Many2one('store.store', name="Store",domain=lambda self: self._domain_store_id())
    scheduling_ids = fields.Many2many('store.scheduling', name="Weeks", domain="[('store_id', '=', store_id)]")

    def _domain_store_id(self):
        user = self.env.user
        if user.has_group('bsi_subway_base.store_owner') or user.has_group('bsi_subway_base.store_admin'):
            return []
        employee = user.employee_id
        return [('id', 'in', employee.store_ids.ids)]

    def print_payroll(self):
        for rec in self:
            report_starting_date = rec.scheduling_ids[0].week_starting_date
            report_ending_date = rec.scheduling_ids[0].week_ending_date
            for dates in rec.scheduling_ids:
                if dates.week_starting_date < report_starting_date:
                    report_starting_date = dates.week_starting_date
                if dates.week_ending_date > report_ending_date:
                    report_ending_date = dates.week_ending_date

            employee_list = []
            data_dict = {}

            store_name = f"Store: {rec.store_id.name}({rec.store_id.store_number})"

            total_week = len(rec.scheduling_ids)
            data_dict['week_count'] = len(rec.scheduling_ids) + 1
            data_dict['store_name'] = store_name or ""


            # For Last Table at Store Level
            store_period_hour_worked_adj = []
            store_period_hour_worked_before_adj = []
            store_period_total_adj = []

            #MP - As per new fields/flow
            # employee_ids = self.env['hr.employee'].search([('store_ids', '=', rec.store_id.id)])
            rec.ensure_one()
            employee_ids = rec.store_id.employee_ids | rec.store_id.store_manager_ids | rec.store_id.district_manager_ids

            global_week_list = []

            for i in range(1, total_week+1):
                global_week_list.append([])

            for sub in global_week_list:
                for i in range(1,5):
                    sub.append([])

            global_header_list = []
            header_list = []
            temp_week_count = 1
            for week in rec.scheduling_ids:
                week_list = rec.get_week_dates(week.week_starting_date, week.week_ending_date)

                if temp_week_count == 1:
                    line_list = ["User ID", "Employee Name"]
                else:
                    line_list = ["", ""]

                if temp_week_count == 1:
                    line_list = line_list + week_list + ['Hrs Worked']
                else:
                    line_list = line_list + week_list + ['']

                header_list.append(tuple(line_list))
                temp_week_count += 1
            header_list.append(tuple(['' , '', 'Wednesday','Thursday','Friday','Saturday','Sunday','Monday','Tuesday','']))
            global_header_list.append(header_list)

            for emp in employee_ids:

                emp_name = emp.name
                # if emp.middle_name:
                #     emp_name += " " + str(emp.middle_name)
                # if emp.last_name:
                #     emp_name += " " + str(emp.last_name) 

                line_data_list = []

                period_total_adj_list = ['', 'PERIOD TOTAL Adj..', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                period_total_before_adj_list = ['', 'PERIOD TOTAL Before Adj..', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                period_adj_amount_list = ['', 'PERIOD Adj. Amount', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

                #Global Master Lists
                global_period_total_adj_list = []
                global_period_total_before_adj_list = []
                global_period_adj_amount_list = []

                week_count = 0
                combine_outer_week_list = []
                for week in rec.scheduling_ids:
                    inner_week_list = []
                    start_date = week.week_starting_date
                    end_date = week.week_ending_date

                    line_list = []
                    date_list = []             
                    current_date = start_date

                    while current_date <= end_date:
                        date_list.append(current_date)
                        current_date += timedelta(days=1)

                    count = 0

                    for date in date_list:
                        min_time = datetime.min.time()
                        # max_time = datetime.max.time()
                        max_time = datetime.max.time().replace(microsecond=0)

                        min_datetime = datetime.combine(date, min_time)
                        max_datetime = datetime.combine(date, max_time)

                        attendance_ids = self.env['hr.attendance'].search([('employee_id', '=', emp.id), 
                            ('store_id', '=', rec.store_id.id), ('check_in', '>=', min_datetime),
                            ('check_in', '<=', max_datetime)
                            ])
                        att_list = []

                        if len(attendance_ids) > count:
                            count = len(attendance_ids)
                    
                    trans_date_list = ['', 'TRANS. DATE']
                    week_list = rec.get_week_dates(week.week_starting_date, week.week_ending_date)
                    trans_date_list = trans_date_list + week_list + ['']
                    
                    total_adj_list = ['', 'TOTAL Adj.', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                    total_before_adj_list = ['', 'TOTAL Before Adj.', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                    adj_amount_list = ['', 'Adj. Amount', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

                    if count > 0:
                        for i in range(1, count+1):
                            print("&&&&&&", i, count)
                            ind = i - 1
                            if i == 1 and week_count == 0:
                                att_list = ['', emp_name]
                            else:
                                att_list = ['', '']

                            # att_sub_list = ['', '']

                            list_ind = 2
                            for date in date_list:

                                min_time = datetime.min.time()
                                max_time = datetime.max.time().replace(microsecond=0)

                                min_datetime = datetime.combine(date, min_time)
                                max_datetime = datetime.combine(date, max_time)

                                attendance_ids = self.env['hr.attendance'].search([('employee_id', '=', emp.id), 
                                    ('store_id', '=', rec.store_id.id), ('check_in', '>=', min_datetime),
                                    ('check_in', '<=', max_datetime)
                                    ])

                                if len(attendance_ids) >= i:
                                    attendance_id = attendance_ids[ind]


                                    #Timezone Update Start

                                    # target_timezone = timezone('America/Indianapolis')
                                    utc = timezone('UTC')

                                    check_in_time_localized = pytz.utc.localize(attendance_id.check_in).astimezone(
                                        pytz.timezone(attendance_id.employee_id._get_tz()))

                                    check_out_time_localized = pytz.utc.localize(attendance_id.check_out).astimezone(
                                        pytz.timezone(attendance_id.employee_id._get_tz()))
                                    #Timezone Update END


                                    previous_check_in_time_localized = False
                                    previous_check_out_time_localized = False
                                    if attendance_id.previous_check_in:
                                        previous_check_in_time_localized = pytz.utc.localize(attendance_id.previous_check_in).astimezone(
                                            pytz.timezone(attendance_id.employee_id._get_tz()))
                                    if attendance_id.previous_check_out:
                                        previous_check_out_time_localized = pytz.utc.localize(attendance_id.previous_check_out).astimezone(
                                            pytz.timezone(attendance_id.employee_id._get_tz()))


                                    logged_hours = " " + str(check_in_time_localized.strftime('%H:%M')) + ' - ' + str(check_out_time_localized.strftime('%H:%M')) + " "
                                    

                                    if previous_check_in_time_localized and not previous_check_out_time_localized:
                                        logged_hours = "<span style='color:blue;'> " + str(previous_check_in_time_localized.strftime('%H:%M')) + "^</span>" + ' - ' + str(check_out_time_localized.strftime('%H:%M')) + " "
                                    
                                    elif previous_check_out_time_localized and not previous_check_in_time_localized:
                                        logged_hours = " " + str(previous_check_out_time_localized.strftime('%H:%M')) + ' - ' + "<span style='color:blue;'>" + str(check_out_time_localized.strftime('%H:%M')) +"^ </span>"
        
                                    elif previous_check_in_time_localized and previous_check_out_time_localized:
                                        logged_hours = "<span style='color:blue;'> " + str(previous_check_in_time_localized.strftime('%H:%M')) + "^</span>" +  ' - ' + "<span style='color:blue;'>" + str(previous_check_out_time_localized.strftime('%H:%M')) +"^ </span>"

                                    logged_hours += " .  (Hrs : " + str(round(attendance_id.worked_hours, 2))+")"
                                    # if previous_check_out_time_localized:
                                    #     logged_hours +=  "\n (Adj Out : " + str(attendance_id.previous_check_out)+")"
                                    # if previous_check_in_time_localized:
                                    #     logged_hours +=  "\n  (Adj In : " + str(attendance_id.previous_check_in)+")"

                                    if previous_check_in_time_localized:
                                        # logged_hours += "\n Adj In : " + previous_check_in_time_localized.strftime('%H:%M') + "*"
                                        logged_hours += (
                                            "<br/> Adj In : <span style='color:red;'>"
                                            + check_in_time_localized.strftime('%H:%M')
                                            + "*</span>"
                                        )
                                    if previous_check_out_time_localized:
                                        # logged_hours += "\n Adj Out : " + previous_check_out_time_localized.strftime('%H:%M') + "*"
                                        logged_hours += (
                                            "<br/> Adj Out : <span style='color:red;'>"
                                            + check_out_time_localized.strftime('%H:%M')
                                            + "*</span>"
                                        )
                                    if previous_check_in_time_localized or previous_check_out_time_localized:

                                        # logged_hours += "\n Adj By : " + str(attendance_id.modified_by_user_id.name) + "*"
                                        logged_hours += (
                                            "<br/> Adj By : <span style='color:red;'>" 
                                            + str(attendance_id.modified_by_user_id.name)
                                            + "*</span>"
                                        )

                                    if list_ind >=2 and list_ind <=8:
                                        total_adj_list[list_ind] += round(attendance_id.worked_hours, 2)
                                        if not attendance_id.previous_check_in and not attendance_id.previous_check_out:
                                            total_before_adj_list[list_ind] += round(attendance_id.worked_hours, 2)
                                            adj_amount_list[list_ind] += round(0, 2)

                                        elif attendance_id.previous_check_in and not attendance_id.previous_check_out:
                                            total_before_adj_list[list_ind] += round((attendance_id.check_out - attendance_id.previous_check_in).total_seconds() / 3600, 2)
                                            adj_amount_list[list_ind] += round(attendance_id.adjustment_difference, 2)

                                        elif not attendance_id.previous_check_in and attendance_id.previous_check_out:
                                            total_before_adj_list[list_ind] += round((attendance_id.previous_check_out - attendance_id.check_in).total_seconds() / 3600, 2)
                                            adj_amount_list[list_ind] += round(attendance_id.adjustment_difference, 2)

                                        elif attendance_id.previous_check_in and attendance_id.previous_check_out:
                                            total_before_adj_list[list_ind] += round((attendance_id.previous_check_out - attendance_id.previous_check_in).total_seconds() / 3600, 2)
                                            adj_amount_list[list_ind] += round(attendance_id.adjustment_difference, 2)

                                    att_list.append(logged_hours)
                                    # att_sub_list.append(worked_hours)
                                else:
                                    att_list.append('')
                                    # att_sub_list.append('')
                                list_ind += 1

                            att_list.append('')
                            # att_sub_list.append('')
                            inner_week_list.append(tuple(att_list))

                    if count == 0 and week_count == 0:
                        att_list = ['', emp_name, '', '', '', '', '', '', '', '']
                        inner_week_list.append(tuple(att_list))

                    inner_week_list.append(tuple(trans_date_list))

                    get_index_total = rec.get_total_from_index(2, 8, total_adj_list)
                    total_adj_list.append(round(get_index_total, 2))
                    inner_week_list.append(tuple(total_adj_list))

                    #Global After Week 
                    global_period_total_adj_list.append(total_adj_list)


                    get_index_total = rec.get_total_from_index(2, 8, total_before_adj_list)
                    total_before_adj_list.append(round(get_index_total, 2))
                    inner_week_list.append(tuple(total_before_adj_list))

                    #Global After Week
                    global_period_total_before_adj_list.append(total_before_adj_list)

                    get_index_total = rec.get_total_from_index(2, 8, adj_amount_list)
                    adj_amount_list.append(round(get_index_total, 2))
                    inner_week_list.append(tuple(adj_amount_list))

                    #Global After Week 
                    global_period_adj_amount_list.append(adj_amount_list)

                    # FOR LAST TABLE OF STORE START
                    store_period_hour_worked_adj.append(total_adj_list[-8:])
                    store_period_hour_worked_before_adj.append(total_before_adj_list[-8:])
                    store_period_total_adj.append(adj_amount_list[-8:])
                    # FOR LAST TABLE OF STORE END

                    # FOR WEEK TABLE START
                    global_week_list[week_count][1].append(total_adj_list)
                    global_week_list[week_count][2].append(total_before_adj_list)
                    global_week_list[week_count][3].append(adj_amount_list)
                    week_count += 1
                    # FOR WEEK TABLE END

                    combine_outer_week_list.append(inner_week_list)

                final_global_period_total_adj_list = rec.get_global_total_from_index(2, 9, global_period_total_adj_list , ['', 'PERIOD TOTAL Adj.'])
                final_global_period_total_before_adj_list = rec.get_global_total_from_index(2, 9, global_period_total_before_adj_list , ['', 'PERIOD TOTAL Before Adj.'])
                final_global_period_adj_amount_list = rec.get_global_total_from_index(2, 9, global_period_adj_amount_list , ['', 'PERIOD Adj. Amount'])
                
                combine_global_period_list = []

                combine_global_period_list.append(tuple(final_global_period_total_adj_list))
                
                combine_global_period_list.append(tuple(final_global_period_total_before_adj_list))
                
                combine_global_period_list.append(tuple(final_global_period_adj_amount_list))

                combine_outer_week_list.append(combine_global_period_list)
                line_data_list.append(combine_outer_week_list)

                employee_list.append(line_data_list)

            store_period_hour_worked_adj = rec.get_store_global_total_from_index(store_period_hour_worked_adj , ['Period Hrs Worked Adj.'])

            store_period_hour_worked_before_adj = rec.get_store_global_total_from_index(store_period_hour_worked_before_adj , ['Period Hrs Worked Before Adj.'])
            store_period_total_adj = rec.get_store_global_total_from_index(store_period_total_adj , ['Period Total Adjustments.'])

            data_count = 0
            for data in global_week_list:
                count = 0
                for line in data:
                    if count != 0:
                        pre_list = []
                        if count == 1:
                            pre_list = ['', 'Hours Worked Adj.']
                        if count == 2:
                            pre_list = ['', 'Hours Worked Before Adj.']
                        if count == 3:
                            pre_list = ['', 'Total Adjustments']
                        result_list = rec.get_global_total_from_index(2, 9, line , pre_list)

                        global_week_list[data_count][count]= result_list[-9:]
                    # data[count] = result_list
                    count += 1
                data_count += 1

            # To Update Week Date line at Week Table
            temp = 0
            for week in rec.scheduling_ids:
                pre_list = ["", "Transaction Date"]
                week_list = rec.get_week_dates(week.week_starting_date, week.week_ending_date)
                result_list =  pre_list + week_list + ['']
                global_week_list[temp][0]= result_list[-9:]
                temp += 1

            data_dict['week_list'] = global_week_list

            store_data_list = []
            store_data_list.append(store_period_hour_worked_adj)
            store_data_list.append(store_period_hour_worked_before_adj)
            store_data_list.append(store_period_total_adj)

            data_dict['header_data'] = global_header_list
            data_dict['employee_data'] = employee_list

            data_dict['store_data'] = store_data_list
            data_dict['start_date'] = report_starting_date
            data_dict['end_date'] = report_ending_date

            return self.env.ref('bsi_subway_base.action_employee_payroll_report').report_action(self, data={'data':data_dict})
            # return {
            #     'type': 'ir.actions.report',
            #     'report_name': 'bsi_subway_base.weekly_payroll_report',
            #     'report_type': 'qweb-html',
            #     'data': {'data': data_dict},
            #     'name': 'Employee Weekly Payroll',
            # }

    def get_week_dates(self, start_date, end_date):
        date_format = "%d/%m/%Y"

        # Generate list of dates
        current_date = start_date
        date_list = []
        
        while current_date <= end_date:
            date_list.append(current_date.strftime(date_format))
            current_date += timedelta(days=1)
        
        return date_list

    def get_total_from_index(self, start_index, end_index, data_list):
        total = 0.0
        if start_index and end_index and data_list:
            for a in data_list:
                if data_list.index(a) >= start_index and  data_list.index(a) <= end_index:
                    total += a
        return total


    def get_global_total_from_index(self, start_index, end_index, data_list, start_list):
        final_list = start_list + [0.0, 0.0 , 0.0, 0.0 , 0.0, 0.0, 0.0, 0.0]

        if start_index and end_index and data_list:
            for sub_list in data_list:
                count = 0
                for a in sub_list:
                    if count >= start_index and  count <= end_index:
                        final_list[count] += a
                    count += 1

        ind_count = 0
        for rec in final_list:
            if ind_count >= start_index and  ind_count <= end_index:
                final_list[ind_count] = round(rec, 2)
            ind_count += 1

        return final_list

    def get_store_global_total_from_index(self, data_list, start_list):
        final_list = [0.0, 0.0 , 0.0, 0.0 , 0.0, 0.0, 0.0, 0.0]

        if data_list:
            for sub_list in data_list:
                count = 0
                for a in sub_list:
                    # if count >= start_index and  count <= end_index:
                    final_list[count] += a
                    count += 1

        ind_count = 0
        for rec in final_list:
            # if ind_count >= start_index and  ind_count <= end_index:
            final_list[ind_count] = round(rec, 2)
            ind_count += 1
        final_list = start_list + final_list

        return final_list
