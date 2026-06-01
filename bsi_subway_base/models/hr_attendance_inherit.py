# -*- coding: utf-8 -*-
from odoo import api, models, fields
from datetime import date
from datetime import datetime, timedelta
import base64
import pytz
from pytz import timezone
from odoo import models, api, exceptions, _
from odoo.exceptions import ValidationError


# RM - 29 Aug [ADD] Need to add new filter/group of store into attendance list view
class HrAttendance(models.Model):
    # _inherit = "hr.attendance"
    _name = "hr.attendance"
    _inherit = ["hr.attendance","mail.thread"]

    store_id = fields.Many2one("store.store", string="Checkin-Store",tracking=True)
    checkout_store_id = fields.Many2one("store.store", string="Checkout-Store")
    is_store_readonly = fields.Boolean(
        compute="_compute_store_readonly",
        store=False
    )

    @api.depends("is_store_readonly")
    def _compute_store_readonly(self):
        user = self.env.user
        for rec in self:
            editable = (
                user.has_group('bsi_subway_base.store_dm') or
                user.has_group('bsi_subway_base.store_owner') or
                user.has_group('bsi_subway_base.store_admin')
            )

            rec.is_store_readonly = not editable


    # RM - 18 SEP [ADD] BASE- overwride
    def _default_employee(self):
        return self.env.user.employee_id

    # RM - 18 SEP [ADD] BASE- overwride
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=True,tracking=True)
    check_out = fields.Datetime(string="Check Out",tracking=True)
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True, ondelete='cascade', index=True,tracking=True)

    # RM - 17 SEP [ADD] If any change in the check-in and check-out entries, the name of the current user is stored in the 'modified by' field.
    previous_check_in = fields.Datetime(string="Previous Check In")
    previous_check_out = fields.Datetime(string="Previous Check Out")
    modified_by_user_id = fields.Many2one('res.users',string="Modified By",tracking=True)
    adjustment_difference = fields.Float(string="Adj. Difference", compute='_compute_adjustment_difference', store=True,tracking=True)
    
    #Check-in & Checkout Location
    check_in_loc = fields.Char(string="Check-In Location")
    check_out_loc = fields.Char(string="Check-Out Location")

    # RM - 4 MAR [ADD] Creation/Update limitation from View.
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(HrAttendance, self).fields_get(allfields, attributes)
        user = self.env.user
        if not user.has_group('bsi_subway_base.store_dm'):
            for field in res:
                res[field]['readonly'] = True
        return res

    # RM - 4 MAR [ADD] Creation/Update limitation from View.
    @api.model
    def create(self, vals):
        res = super(HrAttendance, self).create(vals)
        if not res.store_id and not self.env.user.has_group('bsi_subway_base.store_dm'):
            raise exceptions.AccessError(("You do not have permission to create attendance records."))
        return res

    # RM - 17 SEP [ADD] If any change in the check-in and check-out entries, the name of the current user is stored in the 'modified by' field.
    def write(self, vals):
        for rec in self:
            # check in previous data update on previous check out field only one time.
            if 'check_in' in vals and not rec.previous_check_in:
                vals['modified_by_user_id'] = rec.env.user.id
                vals['previous_check_in'] = rec.check_in

            if 'check_in' in vals and rec.previous_check_in:
                raise ValidationError("You can modify check-in entry only one time.")

            # check out previous data update on previous check out field only one time.
            if 'check_out' in vals and not rec.previous_check_out:
                vals['modified_by_user_id'] = rec.env.user.id
                vals['previous_check_out'] = rec.check_out

            if 'check_out' in vals and rec.previous_check_out:
                raise ValidationError("You can modify check-out entry only one time.")

        result = super(HrAttendance, self).write(vals)
        return result

    # def write(self, vals):
    #     if self.check_in and self.check_out:
    #         if 'check_in' in vals:
    #             vals['modified_by_user_id'] = self.env.user
    #             print("____________vals['modified_by_user_id']___________",vals['modified_by_user_id'])
    #             vals['previous_check_in'] = self.check_in
    #             print("____________vals['previous_check_in']__________",vals['previous_check_in'])
                
    #         if 'check_out' in vals:
    #             vals['modified_by_user_id'] = self.env.user
    #             print("____________vals['modified_by_user_id']___________",vals['modified_by_user_id'])
    #             vals['previous_check_out'] = self.check_out
    #             print("____________vals['previous_check_in']__________",vals['previous_check_in'])
    #     result = super(HrAttendance, self).write(vals)
    #     return result
    
    # RM - 17 SEP [ADD] adjust by counting the difference of check_in and check_out. The difference is stored in the 'Adj. Difference' field.
    @api.depends('check_in', 'check_out', 'previous_check_in', 'previous_check_out')
    def _compute_adjustment_difference(self):
        for record in self:
            if record.previous_check_in and not record.previous_check_out:
                check_in_diff = record.previous_check_in - record.check_in
                print("_______1_____",check_in_diff)
                record.adjustment_difference = check_in_diff.total_seconds() / 3600
                
            elif record.previous_check_out and not record.previous_check_in:
                check_out_diff = record.check_out - record.previous_check_out  
                print("_______2_____",check_out_diff)
                record.adjustment_difference = check_out_diff.total_seconds() / 3600
                
            elif record.previous_check_out and record.previous_check_in:
                previous_check_out_diff = record.previous_check_out - record.previous_check_in
                print("_______3_____",previous_check_out_diff)
                # record.adjustment_difference = previous_check_out_diff.total_seconds() / 3600
                pre_diff = previous_check_out_diff.total_seconds() / 3600
                record.adjustment_difference = record.worked_hours - pre_diff


            else:
                record.adjustment_difference = 0.0

    # RM - 18 SEP [ADD] Click the button and the attendance form view will open
    def open_attendance_form_view(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance',
            'res_id': self.id,
            'target': 'current',
        }

    #MP - Need to convert as per new format: New change, Now we have many2many for SM and DM too at store.
    #GS- Converted Code yet to be tested.
    @api.model
    def _check_district_manager_employee_check_in_out(self):
        final_email_body = """
            <p>Dear Admin,</p>
            <p>Please find below the attendance summary for all district managers' employees:</p>
        """
        # ====================================================================JIGAR======
        dummy_stores=list(i for i in range(222,265)) + [82, 151, 152, 150, 153, 154, 155, 156, 157, 158, 159, 160,
        161, 162, 163, 164, 165, 166, 167]
        store_ids = self.env['store.store'].search([('id', 'not in', dummy_stores )])
        dist_manager_list = []


        store_ids = self.env['store.store'].search([('id', 'not in', dummy_stores)])

        start_date_obj = datetime.now().replace( hour=0, minute=0, second=0, microsecond=0)
        start_date_obj = start_date_obj - timedelta(days=1)

        end_date_obj = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
        end_date_obj = end_date_obj - timedelta(days=1)

        attendance_today = self.env["hr.attendance"].search([
            ("check_in", ">=", start_date_obj),
            ("check_in", "<=", end_date_obj),
        ])

        attended_store_ids = attendance_today.mapped('store_id.id') 
        stores_without_checkin = store_ids.filtered(lambda s: s.id not in attended_store_ids)

        # print('Stores with attendance:', attended_store_ids)
        # print('Stores without attendance:', stores_without_checkin.mapped('name'))

        if stores_without_checkin:
            table0_rows = [
                f"<tr>"
                f"<td>{store.name}</td>"
                f"<td>{', '.join(dm.name for dm in store.district_manager_ids) or 'No District Manager'}</td>"
                f"<td>No Check-In Today</td>"
                f"</tr>"
                for store in stores_without_checkin
            ]

            final_email_body += f"""
                <h3>Stores with Zero Check-Ins on : {start_date_obj.date()}</h3>
                <table border="1" style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr>
                            <th>Store Name</th>
                            <th>District manager</th>
                            <th>Status</th>
                            
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(table0_rows)}
                    </tbody>
                </table>
                <br><br>
            """
        # ====================================================================JIGAR======

        dist_manager_list = []


        dist_manager_ids = self.env['hr.employee'].search([])
        for rec in dist_manager_ids:
            if rec.employee_access_ids:
                for access in rec.employee_access_ids:
                    if access.access_role == 'district_manager':
                        dist_manager_list.append(rec)
                        table1_rows = []
                        table2_rows = []

                        check_in_count_today = 0
                        check_in_count_today_unique_emp = 0

                        missed_check_out_count_today = 0
                        missed_check_in_count_today = 0

                        for store in access.store_ids:
                            empl_list = []
                            for emp in store.employee_ids:
                                if emp.id not in empl_list:
                                    empl_list.append(emp.id)
                            for st_mng in store.store_manager_ids:
                                if st_mng.id not in empl_list:
                                    empl_list.append(st_mng.id)

                            emp_ids = self.env['hr.employee'].browse(empl_list)

                            for employee in emp_ids:
                                target_timezone = timezone(employee._get_tz())
                                utc = timezone('UTC')

                                start_date_obj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                                start_date_obj = start_date_obj - timedelta(days=1)
                                end_date_obj = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
                                end_date_obj = end_date_obj - timedelta(days=1)

                                start_date_localized = target_timezone.localize(start_date_obj).astimezone(utc)
                                end_date_localized = target_timezone.localize(end_date_obj).astimezone(utc)

                                attendance_records = self.env['hr.attendance'].search([
                                    ("employee_id", "=", employee.id),
                                    ("check_in", ">=", start_date_localized),
                                    ("store_id", "=", store.id),
                                    ("check_in", "<=", end_date_localized)                            
                                ])

                                unique_employee_count_att = len(set(attendance.employee_id.id for attendance in attendance_records))
                                check_in_count_today_unique_emp += unique_employee_count_att

                                check_in_count = len(attendance_records.filtered(lambda r: r.check_in))
                                check_out_count = len(attendance_records.filtered(lambda r: r.check_out))
                                missed_check_out_count = check_in_count - check_out_count

                                check_in_count_today += check_in_count

                                missed_check_out_count_today += missed_check_out_count

                                if check_in_count == 0:
                                    missed_check_in_count_today += 1
                                    table2_rows.append(f"""
                                        <tr>
                                            <td>{employee.display_name}</td>
                                            <td>{store.name}</td>
                                            <td>No Clock-In</td>
                                        </tr>
                                    """)

                                for attendance in attendance_records.filtered(lambda r: r.check_in):
                                    emp_check_in = pytz.utc.localize(attendance.check_in).astimezone(
                                        pytz.timezone(employee._get_tz()))
                                    emp_check_in_time = emp_check_in.replace(tzinfo=None)
                                    formatted_check_in_time = emp_check_in_time.strftime('%Y-%m-%d %H:%M:%S')

                                    if attendance.check_out:
                                        emp_check_out = pytz.utc.localize(attendance.check_out).astimezone(
                                            pytz.timezone(employee._get_tz()))
                                        emp_check_out_time = emp_check_out.replace(tzinfo=None)
                                        formatted_check_out_time = emp_check_out_time.strftime('%Y-%m-%d %H:%M:%S')
                                    else:
                                        formatted_check_out_time = 'N/A'

                                    table1_rows.append(f"""
                                        <tr>
                                            <td>{employee.display_name}</td>
                                            <td>{store.name}</td>
                                            <td>{formatted_check_in_time}</td>
                                            <td>{formatted_check_out_time}</td>
                                        </tr>
                                    """)

                        if rec.user_id:
                            if rec.user_id.partner_id:

                                mail_values = {
                                    'subject': f'{start_date_obj.date()}  Employee attendance report for {rec.display_name}',
                                    "email_from": self.env.company.email,
                                    "recipient_ids": [rec.user_id.partner_id.id],
                                    "author_id": 3,
                                    "body_html": f"""
                                        <p><b style="font-size:35px;">Dear {rec.display_name},</b></p>
                                        <p>Please find below the attendance summary for your employees:</p>
                                        <h4>Table 1: Data of employees who did their clock in for :{start_date_obj.date()}</h4>
                                        <p>{check_in_count_today} Count of total attendance entries today.</p>
                                        <p>{check_in_count_today_unique_emp} Number of Unique Employees who did clock-in today..</p>

                                        <table border="1" style="width: 100%; text-align: left; border-collapse: collapse;">
                                            <thead>
                                                <tr>
                                                    <th>Employee Name</th>
                                                    <th>Store Name</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {''.join(table1_rows)}
                                            </tbody>
                                        </table>
                                    """
                                }

                                if missed_check_in_count_today > 0:
                                    mail_values['body_html'] += f"""
                                        <br/><br/><h4>Table 2: Data of employees who didn't their clock in for : {start_date_obj.date()}</h4>
                                        <p>{missed_check_in_count_today} employees today didn't check in</p>
                                        <table border="1" style="width: 100%; text-align: left; border-collapse: collapse;">
                                            <thead>
                                                <tr>
                                                    <th>Employee Name</th>
                                                    <th>Store Name</th>
                                                    <th>Check In Time</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {''.join(table2_rows)}
                                            </tbody>
                                        </table>
                                    """
                                mail_create = self.env['mail.mail'].create(mail_values)
                                mail_create.send()
                    
                        if rec.user_id:
                            final_email_body += f"""<br/><br/>
                                <h4><p style="font-size:35px;">Attendance Report for {rec.display_name} - {start_date_obj.date()}</p></h4>
                                <h5>Table 1: Clock-in Attendance Entries for Today:</h5>
                                <p>{check_in_count_today} Total Clock-in Attendance Entries Found today.</p>
                                <p>{check_in_count_today_unique_emp} Number of Unique Employees who did clock-in today..</p>
                                <table border="1" style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr>
                                            <th>Employee Name</th>
                                            <th>Store Name</th>
                                            <th>Check In Time</th>
                                            <th>Check Out Time</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {''.join(table1_rows)}
                                    </tbody>
                                </table>
                            """

                            if missed_check_in_count_today > 0:
                                final_email_body += f"""
                                    <br/><br/><h5>Table 2: Employees who missed clocking in:</h5>
                                    <p>{missed_check_in_count_today} Missed Expected clocking in today.</p>
                                    <table border="1" style="width: 100%; text-align: left; border-collapse: collapse;">
                                        <thead>
                                            <tr>
                                                <th>Employee Name</th>
                                                <th>Store Name</th>
                                                <th>Missed Clock-In</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {''.join(table2_rows)}
                                        </tbody>
                                    </table>
                            """
        mail_values = {
            'subject': f'Attendance Report for {start_date_obj.date()} - All District Managers',
            'email_from': self.env.company.email,
            'email_to': 'ritik.makadiya@botspotinfoware.com,singh.malkit@gmail.com', 
            'author_id': 3, 
            'body_html': final_email_body,
        }

        mail_create = self.env['mail.mail'].create(mail_values)
        # pdf_content, _ = self.env.ref('bsi_subway_base.dm_att_report_report')._render_qweb_pdf(mail_create.id)

        attachment = self.env['ir.attachment'].create({
            'name': 'Daily report of :'+ str(start_date_obj.date()),
            'type': 'binary',
            # 'datas': base64.b64encode(pdf_content),
            'res_model': 'mail.mail',
            'res_id': mail_create.id,
            'mimetype': 'application/pdf',
            'description': 'Generated PDF from HTML Content',
        })
        mail_create.attachment_ids = [4, attachment.id]
        mail_create.send()
