# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, AccessError, UserError
import re,random,string
import base64
from odoo.modules.module import get_module_resource
from markupsafe import Markup

# _logger = logging.getLogger(__name__)

class HrEmployeeAccess(models.Model):
    _name = "emp.access"
    _description = "Employee Access"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    access_role = fields.Selection(
        [('employee','Employee'),('store_manager','Store Manager'),('district_manager','District Manager')],
        string="Access Role", required=True, tracking=True)
    store_ids = fields.Many2many('store.store', 'store_emp_access',
        string="Stores", required=True, tracking=True)
    store_numbers = fields.Char(string="Store Nos", compute="_compute_store_numbers")
    geo_location_ids = fields.Many2many("emp.geo_location", string="Geo Locations", help="Geo-locations will be appear, once you click on a save button", compute="_compute_geo_location_ids")

    def get_store_member_field_by_access_role(self, role=False):
        field_name = False
        if role == 'employee':
            field_name = 'employee_ids'
        elif role == 'store_manager':
            field_name = 'store_manager_ids'
        elif role == 'district_manager':
            field_name = 'district_manager_ids'
        return field_name

    @api.model_create_multi
    def create(self, vals_list):
        res_ids = super(HrEmployeeAccess, self).create(vals_list)
        for rec in res_ids:
            if rec.access_role and rec.store_ids:
                acc_role_field = rec.get_store_member_field_by_access_role(rec.access_role)
                for store in rec.store_ids:
                    store.sudo().update({acc_role_field: [(4, rec.employee_id.id)]})

            is_post_message = self.env['ir.config_parameter'].sudo().get_param('bsi_subway_base.post_message_in_emp')
            if is_post_message:
                stores = ", ".join([st.name for st in rec.store_ids])                
                message = Markup(f"<b>Added :</b> {rec.access_role} => {stores}")
                rec.employee_id.message_post(
                    body = message,
                    subtype_id=self.env.ref('mail.mt_note').id,  # This sets the subtype to "Note"
                )
        return res_ids

    def write(self, vals):
        old_store_list = self.store_ids.ids
        old_access_role = self.access_role
        old_acc_role_field = self.get_store_member_field_by_access_role(old_access_role)
        old_store_names = ", ".join([st.name for st in self.store_ids])

        result = super(HrEmployeeAccess, self).write(vals)

        new_store_names = ", ".join([st.name for st in self.store_ids])

        if 'access_role' in vals and vals.get('access_role') and 'store_ids' in vals and vals.get('store_ids'):
            new_access_role = vals.get('access_role')
            msg = "You cannot modify both the 'Access Role' and 'Stores' simultaneously. Please remove the access role entry and try again."
            raise ValidationError(msg)

        elif 'access_role' in vals and vals.get('access_role'):
            new_access_role = vals.get('access_role')

            #GS - TO POST MESSAGE
            is_post_message = self.env['ir.config_parameter'].sudo().get_param('bsi_subway_base.post_message_in_emp')
            if is_post_message:
                message = Markup(
                    f"<b>Changed Access Role</b>: <br/>"
                    f"From : <b>{old_access_role} =></b> {new_store_names} <br/>"
                    f"To : <b>{new_access_role} =></b> {new_store_names}"
                )
                self.employee_id.message_post(
                    body = message,
                    subtype_id=self.env.ref('mail.mt_note').id,  # This sets the subtype to "Note"
                )

            if old_access_role:
                new_acc_role_field = self.get_store_member_field_by_access_role(new_access_role)
                for store in old_store_list:
                    store_id = self.env['store.store'].browse(store)
                    if store_id:
                        store_id.sudo().update({
                            old_acc_role_field: [(3, self.employee_id.id)],
                            new_acc_role_field: [(4, self.employee_id.id)],
                            })

        # elif 'store_ids' in vals and vals.get('store_ids'):
        #     new_store_list = vals.get('store_ids')[0][2]
        #     delete_list = []
        #     for old_store in old_store_list:
        #         if old_store in new_store_list:
        #             continue
        #         else:
        #             delete_list.append(old_store)
        #     add_list = []
        #     for new_store in new_store_list:
        #         if new_store in old_store_list:
        #             continue
        #         else:
        #             add_list.append(new_store)
        #     if delete_list:
        #         for delete_store_id in delete_list:
        #             store_id = self.env['store.store'].browse(delete_store_id)
        #             if store_id:
        #                 store_id.sudo().update({old_acc_role_field: [(3, self.employee_id.id)]})
        #     if add_list:
        #         for add_store_id in add_list:
        #             store_id = self.env['store.store'].browse(add_store_id)
        #             if store_id:
        #                 store_id.sudo().update({old_acc_role_field: [(4, self.employee_id.id)]})

        #     #GS - TO POST MESSAGE
        #     is_post_message = self.env['ir.config_parameter'].sudo().get_param('bsi_subway_base.post_message_in_emp')
        #     if is_post_message:
        #         message = f"<b>Changed Stores </b>: <br> From : {self.access_role} <b>=> {old_store_names}</b> <br> To : {self.access_role} <b>=> {new_store_names}</b>"
        #         self.employee_id.message_post(
        #             body = message,
        #             subtype_id=self.env.ref('mail.mt_note').id,  # This sets the subtype to "Note"
        #             email_send=False  # Prevents sending an email notification
        #         )

        elif 'store_ids' in vals and vals.get('store_ids'):
            new_store_list = []
            for command in vals.get('store_ids'):
                if command[0] == 6:  # replace all with new list
                    new_store_list = command[2]
                elif command[0] == 4:  # add single record
                    new_store_list.append(command[1])
                elif command[0] == 3:  # remove single record
                    if command[1] in new_store_list:
                        new_store_list.remove(command[1])
                elif command[0] == 5:  # remove all
                    new_store_list = []

            delete_list = [old for old in old_store_list if old not in new_store_list]
            add_list = [new for new in new_store_list if new not in old_store_list]

            if delete_list:
                for delete_store_id in delete_list:
                    store_id = self.env['store.store'].browse(delete_store_id)
                    if store_id:
                        store_id.sudo().update({old_acc_role_field: [(3, self.employee_id.id)]})

            if add_list:
                for add_store_id in add_list:
                    store_id = self.env['store.store'].browse(add_store_id)
                    if store_id:
                        store_id.sudo().update({old_acc_role_field: [(4, self.employee_id.id)]})

            # GS - TO POST MESSAGE
            is_post_message = self.env['ir.config_parameter'].sudo().get_param('bsi_subway_base.post_message_in_emp')
            if is_post_message:
                message = Markup(
                    f"<b>Changed Stores :</b><br/>"
                    f"<b>From :</b> {self.access_role} => {old_store_names}<br/>"
                    f"<b>To :</b> {self.access_role} => {new_store_names}"
                )
                # message = f"<b>Changed Stores </b>: <br> From : {self.access_role} <b>=> {old_store_names}</b> <br> To : {self.access_role} <b>=> {new_store_names}</b>"
                self.employee_id.message_post(
                    body=message,
                    subtype_id=self.env.ref('mail.mt_note').id,
                )

        return result

    def unlink(self):
        for rec in self:
            if rec.access_role and rec.store_ids:
                acc_role_field = rec.get_store_member_field_by_access_role(rec.access_role)
                for store in rec.store_ids:
                    store.sudo().update({acc_role_field: [(3, rec.employee_id.id)]})

                # GS TO POST THE MESSAGE
                is_post_message = self.env['ir.config_parameter'].sudo().get_param('bsi_subway_base.post_message_in_emp')
                if is_post_message:
                    stores = ", ".join([st.name for st in rec.store_ids])                
                    message = Markup(f"<b>Removed</b>: {rec.access_role} => {stores}")
                    rec.employee_id.message_post(
                        body = message,
                        subtype_id=self.env.ref('mail.mt_note').id,  # This sets the subtype to "Note"
                    )
        return super(HrEmployeeAccess, self).unlink()

    @api.depends('store_ids')
    def _compute_store_numbers(self):
        for rec in self:
            numbers = ''
            if rec.store_ids:
                for store in rec.store_ids:
                    if store.store_number:
                        if not numbers:
                            numbers = str(store.store_number)
                        else:
                            numbers += ', ' + str(store.store_number)
            rec.store_numbers = numbers

    @api.depends('store_ids')
    def _compute_geo_location_ids(self):
        for rec in self:
            location_ids = []
            if rec.store_ids:
                for store in rec.store_ids:
                    if store.geo_location_id:
                        location_ids.append((store.geo_location_id.id))
            rec.geo_location_ids = location_ids

    _sql_constraints = [
        ('unique_employee_access_role', 'unique(employee_id, access_role)', 
         'An employee cannot have duplicate access roles. Please discard these changes and add the store to the existing access role.')
    ]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    # _rec_name = 'display_combine_name'
    
    per_hr_wage = fields.Float(string="Per Hour Wage")
    # display_combine_name = fields.Char(string="Name",compute="_compute_name")
    # name = fields.Char(string="First Name", required=True,tracking=True,copy=True)
    first_name = fields.Char(string="First Name", required=True,tracking=True,copy=True)
    middle_name = fields.Char(string="Middle Name", tracking=True)
    last_name = fields.Char(string="Last Name", help="Maximum of 15 characters allowed.", required=True,tracking=True)
    
    # store_no = fields.Integer(string="Store No.", required=True,tracking=True)
    # type_of_employee = fields.Selection([('employee','Employee'),('store_manager','Store Manager'),('district_manager','District Manager')],string="Employee Type",required=True,tracking=True)
    # store_id = fields.Many2one('store.store',string="Store")
    # store_ids = fields.Many2many('store.store', 'employee_id' , string="Stores" , tracking = True)
    # geo_location_ids = fields.Many2many("emp.geo_location", string="Geo Locations", compute="_compute_geo_location_ids")
    tz = fields.Selection(string='Timezone', related='resource_id.tz', readonly=False, tracking = True)

    employee_access_ids = fields.One2many("emp.access", "employee_id", string="Employee Store Access", copy=False)

    ssn_no = fields.Integer(string="SSN No", help="Must be 9 digits.", required=False,tracking=True)
    date_of_birth = fields.Date(string="Date of  Birth", required=False,tracking=True)
    email_id = fields.Char(string="Email ID", required=True, tracking=True)
    gender = fields.Selection([("", ""),("male", "Male"),("female", "Female")],required=False,tracking=True)

    cell_no_1 = fields.Char(string="Cell No 1", required=False,tracking=True)
    cell_no_2 = fields.Char(string="Cell No 2", required=False,tracking=True)
    cell_no_3 = fields.Char(string="Cell No 3", required=False,tracking=True)

    address = fields.Char(string="Address", help="Street Address", required=False,tracking=True)
    address_line_2 = fields.Char(string="Address Line 2", help="Street Address", required=False,tracking=True)
    city = fields.Char(string="City", help="City", required=False,tracking=True)
    postal_zip_code = fields.Integer(string="Postal/Zip Code", help="Postal/Zip Code", required=False,tracking=True)
    state = fields.Many2one("res.country.state",string="State",help="State / Province / Region",required=False,tracking=True,copy=True)
    country = fields.Many2one("res.country", string="Country", help="Country", required=False,tracking=True)

    legal_entity_name = fields.Char(string="Legal Entity name", required=False,tracking=False)
    # franchise_name = fields.Char(string="Franchise Name", required=False,tracking=False)
    franchise_name = fields.Selection([("", ""),("subway", "Subway"),("biggby", "Biggby"),("hangry_joe's", "Hangry Joe's")],required=False,tracking=True)

    hired_date = fields.Date(string="Hired Date", required=False,tracking=False)
    employment_type = fields.Selection([("", ""),("full_time", "Full Time"),("part_time", "Part_Time"),],required=False,tracking=True)
    employment_title = fields.Selection([("", ""),("sandwich_artist", "Sandwich Artist"),("assistant_store_manager", "Assistant Store Manager"),("store_manager", "Store Manager"),],required=False,tracking=True)

    type_of_compensation = fields.Selection([("", ""),("hourly_rate", "Hourly Rate"),("salary", "Salary"),],required=False,tracking=True)
    hourly_rate = fields.Integer(string="Hourly Rate",tracking=True)
    salary = fields.Integer(string="Salary",tracking=True)
    dollars = fields.Integer(string="Dollars",tracking=True)
    cents = fields.Integer(string="Cents",tracking=True)

    name_of_bank = fields.Char(string="Name of Bank",tracking=True)
    account_no = fields.Char(string="Account No.",tracking=True)
    routing_no = fields.Integer(string="Routing No.",tracking=True)
    account_type = fields.Selection([("saving", "Saving"),("checking", "Checking"),],tracking=True)

    filing_status = fields.Selection([("", ""),("single", "Single"),("married", "Married"),],required=False,tracking=True)
    no_of_dependents_claimed_in_form_w4_line_5 = fields.Selection([("", ""),("0", "0"),("1", "1"),("2", "2"),("3", "3"),("4", "4"),("5", "5"),("6", "6"),("7", "7"),("8", "8"),("9", "9"),("10", "10"),],string="No of dependents claimed in form W4 (line 5)",required=False,tracking=True)
    ipc_tax_credit_form_wotc = fields.Char(string="IPC Tax Credit Form (WOTC)", required=False,tracking=True)

    form_w4 = fields.Many2many("ir.attachment", "att_rel_new", string="Form W4", tracking=True)
    ssn_card = fields.Many2many("ir.attachment", "att_rel__new_1", string="SSN Card", tracking=True)
    form_i9 = fields.Many2many("ir.attachment", "att_rel_new_2", string="Form I9", tracking=True)
    id_proof = fields.Many2many("ir.attachment","att_rel_new_3",string="ID Proof (like Driving Licence, etc )",tracking=True)
    irs_online_w2_and_paysub_acceptance = fields.Many2many("ir.attachment","att_rel_new_4",string="IRS Online W2 & Paystub Acceptance",tracking=True)
    work_permit = fields.Many2many("ir.attachment", "att_rel_new_5", string="Work permit (If applicable)",tracking=True)
    insurance_enrollment_for_obama_care = fields.Many2many("ir.attachment", "att_rel_new_6", string="Insurance Enrollment for Obama Care",tracking=True)
    electronic_pay_card = fields.Many2many("ir.attachment", "att_rel_new_7", string="Electronic Pay Card", tracking=True)
    others = fields.Many2many("ir.attachment", "att_rel_new_8", string="Others",tracking=True)

    page_2_terms_and_conditions = fields.Text(string="Page 2 Data",compute="_compute_page_2_terms_and_conditions",required=False,tracking=True)
    page_3_terms_and_conditions = fields.Text(string="Page 3 Data",compute="_compute_page_3_terms_and_conditions",required=False,tracking=True)
    terms_and_conditions = fields.Boolean(string="Terms & Conditions",tracking=True)
    terms_and_conditions_msg = fields.Text(string="Message", compute="_compute_terms_and_conditions_msg",tracking=True)
    # related_user_id = fields.Many2one('res.users',string="Related User",tracking=True,copy=False)

    # GS FEB6 
    store_ids = fields.Many2many('store.store', 'employee_id' , string="Allowed Scheduling Stores", copy=False)
    user_ids = fields.Many2many('res.users', 'employee_rel', string="Superior Users", copy=False)

    #APR23 - API Test
    bypass_att = fields.Boolean(string="Bypass Checkin")

    req_emp_fields = fields.Boolean(string="Req Emp Fields?", default=True)

    application_state=fields.Selection([
            ('draft_state', 'Draft'),
            ('notify_employee', 'Notify Employee'),
            ('request_store_access', 'Request store access'),
            ('onboarded', 'Onboarded')
        ],default='draft_state'
    )

    @api.onchange('type_of_compensation')
    def _onchange_type_of_compensation(self):
        for rec in self:
            rec.dollars = 0
            rec.cents = 0

            if rec.type_of_compensation == 'hourly_rate':
                rec.salary = 0

            elif rec.type_of_compensation == 'salary':
                rec.hourly_rate = 0

            else:
                rec.hourly_rate = 0
                rec.salary = 0

    @api.constrains('first_name', 'middle_name', 'last_name')
    def _check_name_format(self):
        for rec in self:
            fields_to_check = {
                "First Name": rec.first_name,
                "Middle Name": rec.middle_name,
                "Last Name": rec.last_name,
            }

            for label, value in fields_to_check.items():
                if value:
                    if value != value.capitalize():
                        raise ValidationError(
                            f"{label} must be properly capitalized "
                            "(e.g. John)"
                        )

    # RM [26Dec-2025] [ADD - signature in pdf - START]
    is_policy_signed = fields.Boolean(string="Is Policy Signed", default=False)

    #Retrict Users from deleting the Employees.
    def unlink(self):
        # Allow only System Administrators to delete employees
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_(
                "You are not allowed to delete employee records.\n\n"
                "Please archive the employee instead of deleting it."
            ))
        res = super(HrEmployee, self).unlink()
        return res

    def _get_default_pdf_content(self):
        file_path = get_module_resource('bsi_subway_base', 'static/src', 'New_Hire_Packet_updated.pdf')
        if file_path:
            with open(file_path, 'rb') as f:
                return base64.b64encode(f.read())
        return False

    def _get_default_pdf_name(self):
        return "Click here see the Hiring Policy.pdf"

    custom_pdf_filename = fields.Char(string="File Name", default=_get_default_pdf_name)
    custom_pdf_file = fields.Binary(
        string="Product Document", 
        default=_get_default_pdf_content, 
        attachment=True
    )

    def action_replace_with_signed_pdf(self):
        report_xml_id = 'bsi_subway_base.action_report_new_hire_packet'
        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report_xml_id, self.ids)

        if pdf_content:
            encoded_pdf = base64.b64encode(pdf_content)
            filename = f"Click here see the Signed Hiring Policy.pdf"
            current_user = self.env.user.name

            self.write({
                'custom_pdf_file': encoded_pdf,
                'custom_pdf_filename': filename,
                'is_policy_signed': True
            })

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': encoded_pdf,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })

            log_message = f"Digital signature PDF has been updated by {current_user}."
            self.message_post(
                body=log_message,
                attachment_ids=[attachment.id]
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Signed PDF has been attached successfully by {current_user}!',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
    # RM [26Dec-2025] [ADD - signature in pdf - END]

    def set_state_draft(self):
        self.application_state='draft_state'

    def request_store_access(self):
        self.ensure_one()
        required_fields = ['date_of_birth',
            'cell_no_1', 'cell_no_2', 'cell_no_3',
            'gender', 'tz', 'address', 'address_line_2', 'city', 'postal_zip_code', 'state', 'country',
            'legal_entity_name', 'franchise_name', 'hired_date', 'employment_type',
            'type_of_compensation', 'per_hr_wage',
            'filing_status', 'no_of_dependents_claimed_in_form_w4_line_5', 'ipc_tax_credit_form_wotc',
            'form_w4', 'ssn_card', 'form_i9', 'id_proof',
            'irs_online_w2_and_paysub_acceptance',
            'insurance_enrollment_for_obama_care', 'electronic_pay_card', 'others',
            'terms_and_conditions', 'dollars'
        ]
        # 'name_of_bank', 'account_no', 'routing_no', 'account_type',
        missing_fields = []

        for field_name in required_fields:
            value = getattr(self, field_name)
            field_type = self._fields[field_name].type

            if field_type in ['many2many', 'one2many']:
                if not value:
                    missing_fields.append(field_name)
            elif field_type in ['char', 'text', 'selection', 'many2one', 'boolean', 'date', 'datetime']:
                if value in (False, '', None):
                    missing_fields.append(field_name)
            elif field_type in ['integer', 'float', 'monetary']:
                if value is None:
                    missing_fields.append(field_name)

        if self.req_emp_fields:
            if missing_fields:
                readable_fields = [f.replace('_', ' ').title() for f in missing_fields]
                raise UserError(
                    "The following fields are required and cannot be empty before notifying the employee:\n\n" +
                    "\n".join(readable_fields)
                )
        district_manager_email = self.create_uid.email

        full_name=str(self.first_name+' '+self.middle_name+' '+self.last_name)
        dm_name = str(self.create_uid.name)
        mail_values = {
            'subject': f"Store Access Request – {full_name}",
            'email_to': district_manager_email,
            'email_from': self.email_id,
            'email_cc': self.email_id,
            'body_html': f"""
                <p>Dear District Manager({dm_name}),</p>

                <p>I, <b>{full_name}</b>, have completed all my profile information and would like to request store access.</p>

                <p><b>Employee Details:</b></p>
                <p>
                    <b>Full Name:</b> {full_name}<br/>
                    <b>Email:</b> {self.email_id}<br/>
                    <b>Job Title:</b> {self.job_title or 'N/A'}<br/>
                    <b>Franchise / Store:</b> {self.franchise_name or 'N/A'}
                </p>

                <p>Please review my profile and assign the store at your earliest convenience.</p>

                <br/>
                <p>Thank you,<br/>
                {full_name}</p>
            """,
        }


        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.sudo().send()

        self.application_state = "request_store_access"

    def onboard_and_notify_employee(self):
        if not self.employee_access_ids:
            raise UserError(
                "Assign an access role to the employee to complete onboarding"
            )

        # assigned_stores = ", ".join(store.name for store in self.employee_access_ids.store_ids) if self.employee_access_ids.store_ids else "N/A"
        # access_role = self.employee_access_ids.access_role
        full_name=str(self.first_name+' '+self.middle_name+' '+self.last_name)
        access_data = {}
        for access in self.employee_access_ids:
            stores = ", ".join(store.name for store in access.store_ids)
            access_data[access.access_role] = stores

        role_string = ""
        for role,store in access_data.items():
            role_string += f"""
                <p>
                    <b>Role:</b> {role}<br/>
                    <b>Assigned Store(s):</b> {store}
                </p>
                """
        mail_values = {
            'subject': f"Onboarding Completed – {full_name}",
            'email_to': self.email_id,
            'email_from': self.env.user.email,  
            'body_html': f"""
                <p>Dear <b>{full_name}</b>,</p>

                <p>Congratulations! Your onboarding process has been successfully completed.</p>

                <p><b>Your Access Details:</b></p>
                {role_string}
                <p>You can now log in to the Employee Portal to view your profile, assigned stores, and perform your Attendance(Clock-In/Clock-Out).</p>

                <p>Login link: 
                <a href="{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}">
                {self.env['ir.config_parameter'].sudo().get_param('web.base.url')}</a></p>

                <br/>
                <p>Best regards,<br/>
                Admin Team</p>
            """,
        }

        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.sudo().send()

        self.application_state='onboarded'    

    
    #RM - [23/07/2025] - Archive button click to employee and this employee user archive.
    def action_archive(self):
        for employee in self:
            if employee.user_id and employee.user_id.active:
                employee.user_id.sudo().write({'active': False})
                # employee.user_id.active = False
        return super(HrEmployee, self).action_archive()

    #RM - [23/07/2025] - Unarchive button click to employee and this employee user unarchive.
    def action_unarchive(self):
        for employee in self:
            if employee.user_id and not employee.user_id.active:
                # employee.user_id.active = True
                employee.user_id.sudo().write({'active': True})
        return super(HrEmployee, self).action_unarchive()

    #RM - FEB7 - email format validation.
    # @api.constrains('email_id')
    # def _check_valid_email(self):
    #     email_format = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    #     for rec in self:
    #         if rec.email_id and not re.match(email_format, rec.email_id):
    #             raise ValidationError("Please add valid email.")

    #RM - OCT3 - Account No. field data type change to Char.
    @api.constrains('account_no')
    def _check_account_no_field(self):
        for record in self:
            if record.account_no and not record.account_no.isdigit():
                raise ValidationError("Only numeric values are allowed in the Account No. Field.")

    @api.constrains('tz')
    def tz_constrains(self):
        for rec in self:
            if rec.tz and rec.user_id:
                if rec.user_id.tz != rec.tz:
                    rec.user_id.tz = rec.tz

    #MP - User will be only generated once we 'ACTIVE' it, so added this fun calling on 'ACTIVE' feat.
    # GS-OCT21 To update m2m of user
    # @api.model
    # def create(self, vals):
    #     if 'name' not in vals:
    #         full_name = ""
    #         if vals['first_name']:
    #             full_name += vals['first_name']
    #         if vals['middle_name']:
    #             full_name =  full_name + " " + vals['middle_name']
    #         if vals['last_name']:
    #             full_name =  full_name + " " + vals['last_name']
    #         vals['name'] = full_name
    #     result = super(HrEmployee, self).create(vals)
    #     return result

    def create(self, vals):
        # Check if vals is a list (multiple records)
        if isinstance(vals, list):
            # Loop through each dictionary in the list
            for v in vals:
                if not v.get('name'):
                    parts = [v.get('first_name') or '', v.get('middle_name') or '', v.get('last_name') or '']
                    v['name'] = " ".join(p for p in parts if p).strip()
        else:
            # Single record case
            if not vals.get('name'):
                parts = [vals.get('first_name') or '', vals.get('middle_name') or '', vals.get('last_name') or '']
                vals['name'] = " ".join(p for p in parts if p).strip()

        result = super(HrEmployee, self).create(vals)
        return result



    # def create(self, vals):
    #     if not vals.get('name'):
    #         # fallback if first/middle/last are in vals
    #         parts = [vals.get('first_name') or '', vals.get('middle_name') or '', vals.get('last_name') or '']
    #         vals['name'] = " ".join(p for p in parts if p).strip()
    #     result = super(HrEmployee, self).create(vals)
    #     return result

    def write(self,vals):
        result = super(HrEmployee, self.sudo()).write(vals)
        if any(f in vals for f in ['first_name', 'middle_name', 'last_name']):
            for rec in self:
                rec.name = rec.prepare_full_name()

        if 'email_id' in vals:
            self.sudo().user_partner_id.email = vals.get('email_id')
            email = vals.get('email_id').lower()
            if self.user_id:
                self.user_id.sudo().write({'login': email})
                if self.user_id.partner_id:
                    self.user_id.partner_id.sudo().write({'email': email})

        if 'employee_access_ids' in vals:
            self.assign_higher_access_role_group_to_user()
            self.env.user.compute_domain_employee_ids()
            self.get_allowed_scheduling_stores()
            self.get_superior_users()

            #GS- To Update again superior_users when change in related stores's emp's access lines
            for rec in self.sudo().employee_access_ids:
                for store in rec.sudo().store_ids:
                    for emp in store.sudo().employee_ids:
                        if emp.id != self.id:
                            emp.sudo().get_superior_users()
                    for sm in store.sudo().store_manager_ids:
                        if sm.id != self.id:
                            sm.sudo().get_superior_users()

                    for dm in store.sudo().district_manager_ids:
                        if dm.id != self.id:
                            dm.sudo().get_superior_users()

            #MP - Query: Why we'are updating all the users's employees??
            # self.user_id.compute_domain_employee_ids()
        return result

    #GS FEB6 to Find Allowed Scheduling Stores
    def get_allowed_scheduling_stores(self):
        allowed_scheduling_stores = []
        for rec in self.sudo().employee_access_ids:
            if rec.access_role in ['store_manager', 'district_manager']:
                allowed_scheduling_stores += rec.store_ids.ids
        self.store_ids = False
        self.sudo().write({'store_ids' : allowed_scheduling_stores})
        # self.sudo().store_ids = allowed_scheduling_stores

    def get_superior_users(self):
        superior_users = []
        # if self.user_id:
        #     superior_users.append(self.user_id.id)
        for rec in self.sudo().employee_access_ids:

            if rec.sudo().access_role == 'district_manager':
                for store in rec.sudo().store_ids:
                    for dm in store.sudo().district_manager_ids:
                        if dm.user_id and dm.user_id.id not in superior_users:
                            if dm.user_id.id != self.user_id.id:
                                superior_users.append(dm.user_id.id)

            if rec.sudo().access_role == 'store_manager':
                for store in rec.sudo().store_ids:
                    for dm in store.sudo().district_manager_ids:
                        if dm.user_id and dm.user_id.id not in superior_users:
                            superior_users.append(dm.user_id.id)

            if rec.access_role == 'employee':
                for store in rec.store_ids:
                    for dm in store.district_manager_ids:
                        if dm.user_id and dm.user_id.id not in superior_users:
                            superior_users.append(dm.user_id.id)
                    for sm in store.store_manager_ids:
                        if sm.user_id and sm.user_id.id not in superior_users:
                            superior_users.append(sm.user_id.id)

        self.user_ids = False
        self.sudo().write({'user_ids' : superior_users})
        self.sudo().user_ids = superior_users

    @api.depends("first_name", "last_name")
    def _compute_page_2_terms_and_conditions(self):
        for record in self:
            record.page_2_terms_and_conditions = str(
            "Employers are required by the Internal Revenue Service (IRS) to provide each employee with a W-2 Form that states the employee’s compensation and tax withholding amounts for the calendar year on or before January 31st of the following year."
            + "Previously we provided paper copies of W-2’s. In 2004 the IRS approved the use of electronic W-2 statements. Starting this year, instead of paper copies, employees may choose to receive their W-2 statement electronically."
            + "The benefits of receiving an electronic W-2 statement are:"
            + " Earlier access"
            + " Once received electronically, significantly less possibility that the W-2 may be lost or stolen"
            + " Access is possible electronically if the employee is away from his/her usual home or work location"
            + "Compensation and tax withholding information may easily be downloaded into many tax preparation software programs"
            + "Employers must comply with specific IRS regulations to use electronic W-2’s and employees must provide their consent to receive an electronic W-2 instead of a paper copy. This notice contains the required IRS disclosure information and instructions for you to consent to receiving your W-2 electronically instead of a paper copy. If you have any questions regarding this notice or your W-2 Statement, contact the HR Department."
            + "Please read this entire notice and, if you wish to receive all future W-2 statements from this company electronically, provide your consent by clicking “I agree” button. If you do not provide this consent by January 27th, you will continue to receive a paper copy of your W-2 statement."
            + "As required by the IRS, this consent must be made electronically in a manner that reasonably demonstrates that the employee can access the W-2 in the electronic format in which it will be provided. As an alternative, the consent may be made via e-mail or via a paper authorization if it is confirmed electronically in a manner that demonstrates the employee’s ability to access the electronic statement."
            + "To assure compliance with this requirement, employees who wish to receive their W-2 electronically, must:"
            + "Go to www.connivia.com and click on W2 Download"
            + "If you are unable to provide consent in this preferred manner, please contact the HR Department no later than Jan 27th. This consent will cease if the employee is no longer employed with us."
            + "An employee who chooses to receive his/her W-2 statement electronically may withdraw consent. The employee’s withdrawal of consent will be effective on the date it is received and the Payroll Department will confirm in writing or by e-mail the effective date of the consent withdrawal."
            + "If consent is withdrawn, it will only be effective for those W-2 statements not yet issued."
            + "To withdraw your consent, send an e-mail or written notice to:"
            + "Payroll Department: Address: 315 us highway 31 S, Greenwood, IN Phone Number: 317-497-5071 E-mail address: Payroll@connivia.com In addition, an employee’s written request to receive a paper copy will be considered a withdrawal of consent for electronic delivery."
            + "If an employee consents to electronic W-2 delivery and the delivery is unable to be made due to a technical problem, incorrect login or password, incorrect e-mail address, the employee will receive a paper copy. If there is any change in how to receive electronic delivery, employees will be notified immediately via e-mail or written notice. Employees are also required to inform the HR Department promptly of any personal address or status changes through the email or by written notification."
            + "Electronic W-2 statements will be accessible from Jan 25th2017. (IRS requires that they are posted through October 15th of the year following the calendar year applicable for the Form.)"
            + "If you completed the electronic consent correctly, you will be able to Download your W2 in next screen."
            )

    @api.depends("first_name", "last_name")
    def _compute_page_3_terms_and_conditions(self):
        for record in self:
            record.page_3_terms_and_conditions = str(
            "Terms and conditions : “Hybrid Accounting is providing web based third party services to the clients and hence we are not responsible for employment terms and any other applicable laws for employment.” "
            + "We are not responsible for data theft, manipulation or misuse of data by any other source during transition. The user assumes all responsibility and risk"
            + "for the use of this Website and the Internet generally. We accept no liability or responsibility to any person or organisation as a consequence of any reliance upon the information contained or filed in this site. Under no circumstances, including negligence, shall anyone involved in creating or maintaining this Website be liable for any direct, indirect, incidental, special or consequential damages, or loss profits that result from the use or inability to use the Website and/or any other websites which are linked to this site. Nor shall they be liable for any such damages including, but not limited to, reliance by a member or visitor on any information obtained via the Website; or that result from mistakes, omissions, interruptions, deletion of files, viruses, errors, defects, or failure of performance, communications failure, theft, destruction or unauthorized access.States or Countries which do not allow some or all of the above limitations of liability, liability shall be limited to the greatest extent allowed by law."
            )

    @api.depends("first_name", "last_name")
    def _compute_terms_and_conditions_msg(self):
        for record in self:
            record.terms_and_conditions_msg = str(
            "I acknowledge that I have read and agree to the above Terms and Conditions"
            )

    # @api.constrains('first_name', 'middle_name', 'last_name')
    def prepare_full_name(self):
        """Build full name from record fields only."""
        self.ensure_one()
        parts = [self.first_name or '', self.middle_name or '', self.last_name or '']
        return " ".join(p for p in parts if p).strip()


    # [RM - SEP 11/2025 - Display Full Name Show]
    # @api.constrains('first_name', 'middle_name', 'last_name')
    # def display_full_name(self):
    #     print("_____________________________")
    #     for rec in self:
    #         print("_______rec______________________",rec,rec.name,rec.display_name)
    #         parts = [rec.name or '', rec.middle_name or '', rec.last_name or '']
    #         print("_________parts____________________",parts)
    #         display_name = " ".join(p for p in parts if p).strip()
    #         rec.update({'display_name':display_name})
    #         print("_____________rec.display_name________________",rec.display_name)

    # @api.depends('first_name','middle_name','last_name')
    # def _compute_name(self):
    #     for rec in self:
    #         display_combine_name = False
    #         if rec.name :
    #             display_combine_name = rec.name
    #         if rec.middle_name:
    #             display_combine_name += ' '+rec.middle_name
    #         if rec.last_name:
    #             display_combine_name += ' '+rec.last_name
    #         rec.display_combine_name = display_combine_name


    # remove Employee, Store manager, District Manager 'Store Access'.
    def remove_all_store_access_roles(self):
        store_employee_group = self.env.ref('bsi_subway_base.store_employee')
        subway_store_manager_group = self.env.ref('bsi_subway_base.store_manager')
        subway_district_manager_group = self.env.ref('bsi_subway_base.store_dm')
        if self.user_id in subway_district_manager_group.users:
            subway_district_manager_group.sudo().write({'users': [(3, self.user_id.id)]})
        if self.user_id in subway_store_manager_group.users:
            subway_store_manager_group.sudo().write({'users': [(3, self.user_id.id)]})
        if self.user_id in store_employee_group.users:
            store_employee_group.sudo().write({'users': [(3, self.user_id.id)]})

    # Assign top access role for created user
    # Ex: if emp is SM and DM, then will be provided DM access
    def assign_higher_access_role_group_to_user(self):
        for rec in self:
            if rec.user_id:
                store_employee_group = self.env.ref('bsi_subway_base.store_employee')
                subway_store_manager_group = self.env.ref('bsi_subway_base.store_manager')
                subway_district_manager_group = self.env.ref('bsi_subway_base.store_dm')

                #Attendance Group Update July 18
                att_admin_group = self.env.ref('hr_attendance.group_hr_attendance_manager')
                att_officer_group = self.env.ref('hr_attendance.group_hr_attendance_officer')
                manual_att_group = self.env.ref('hr_attendance.group_hr_attendance_own_reader')

                #Employee Group Update July 18
                emp_admin_group = self.env.ref('hr.group_hr_manager')
                emp_officer_group = self.env.ref('hr.group_hr_user')
                # att_kiosk_group = self.env.ref('hr_attendance.group_hr_attendance_kiosk')

                # [RM - SEP 11/2025 - Show Attendance Menu]
                att_show_menu_group = self.env.ref('hr_attendance.group_hr_attendance_officer')

                if rec.employee_access_ids:
                    roles = rec.employee_access_ids.mapped('access_role')
                    if 'district_manager' in roles:
                        subway_district_manager_group.sudo().write({'users': [(4, rec.user_id.id)]})

                        #Remove Admin and Add Officer From Employee
                        emp_admin_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        emp_officer_group.sudo().write({'users': [(4,rec.user_id.id)]})

                        #Remove Admin,Officer and Add Manual in Attendance
                        att_admin_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        att_officer_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        manual_att_group.sudo().write({'users': [(4,rec.user_id.id)]})

                        # [RM - SEP 11/2025 - Show Attendance Menu]
                        att_show_menu_group.sudo().write({'users': [(4,rec.user_id.id)]})

                    elif 'store_manager' in roles:
                        subway_store_manager_group.sudo().write({'users': [(4,rec.user_id.id)]})
                        if rec.user_id in subway_district_manager_group.users:
                            subway_district_manager_group.sudo().write({'users': [(3, rec.user_id.id)]})

                        #Remove Admin and Add Officer From Employee
                        emp_admin_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        emp_officer_group.sudo().write({'users': [(4,rec.user_id.id)]})

                        #Remove Admin,Officer and Add Manual in Attendance
                        att_admin_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        att_officer_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        manual_att_group.sudo().write({'users': [(4,rec.user_id.id)]})

                        # [RM - SEP 11/2025 - Show Attendance Menu]
                        att_show_menu_group.sudo().write({'users': [(4,rec.user_id.id)]})

                    elif 'employee' in roles:
                        store_employee_group.sudo().write({'users': [(4,rec.user_id.id)]})
                        if rec.user_id in subway_district_manager_group.users:
                            subway_district_manager_group.sudo().write({'users': [(3, rec.user_id.id)]})
                        if rec.user_id in subway_store_manager_group.users:
                            subway_store_manager_group.sudo().write({'users': [(3, rec.user_id.id)]})
                        
                        #Attendance Group Update July 18
                        att_admin_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        att_officer_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        manual_att_group.sudo().write({'users': [(4,rec.user_id.id)]})
                        
                        #Employee Group Update July 18
                        if rec.application_state != 'request_store_access' and not rec.user_id.has_group('bsi_subway_base.store_employee'):
                            emp_admin_group.sudo().write({'users': [(3,rec.user_id.id)]})
                            emp_officer_group.sudo().write({'users': [(3,rec.user_id.id)]})
                        # att_kiosk_group.sudo().write({'users': [(4,rec.user_id.id)]})

                        # [RM - SEP 11/2025 - Show Attendance Menu]
                        att_show_menu_group.sudo().write({'users': [(4,rec.user_id.id)]})

                    else:
                        rec.remove_all_store_access_roles()

                else:
                    rec.remove_all_store_access_roles()

    def notify_employee(self):
        if not self.tz:
            raise ValidationError("Please select a timezone for the employee to create a user.")
        vals = {}
        res_user_id = self.env['res.users'].search([('login','=',self.email_id)], limit=1)
        if res_user_id:
            raise ValidationError("You can not have two users with the same login/email!")
        else:
            email = self.email_id
            email = email.lower()
            parts = [self.first_name or '', self.middle_name or '', self.last_name or '']
            full_name = " ".join(p for p in parts if p).strip()
            vals = {'name': full_name,'login': email, 'tz': self.tz}
        if vals:
            user_id = self.env['res.users'].sudo().create(vals)
            if user_id:
                self.user_id = user_id
                # Assign store access rights in user
                self.assign_higher_access_role_group_to_user()
                # Assign sub employees once create user_id
                self.env.user.sudo().compute_domain_employee_ids()
                
            if user_id and self.user_id.partner_id:
                self.user_id.partner_id.sudo().write({'email': self.email_id})
                
        if self.resource_calendar_id:
            self.resource_calendar_id = False

        if user_id:
            # if self.dollars <= 0:
            #     raise UserError("Hourly Rate / Salary must be greater than 0.")
                
            if not self.email_id or not self.first_name or not self.last_name or not self.middle_name or not self.type_of_compensation or not self.dollars:
                    raise UserError(
                        """The following fields are required and cannot be left blank:
                        - First Name
                        - Middle Name
                        - Last Name
                        - Work Email
                        - Type of Compensation
                        - Hourly Rate/Salary
                        
                        Please fill in these details before creating the user and clicking the 'Notify Employee' button."""
                    )
            full_name=str(self.first_name+' '+self.middle_name+' '+self.last_name)
            digits = random.choices(string.digits, k=3)  
            letters = random.choices(string.ascii_letters, k=3)  
            password_list = digits + letters
            random.shuffle(password_list)
            password = ''.join(password_list)
            store_emp_group = self.env.ref('bsi_subway_base.store_employee')
            self.user_id.sudo().write({'password':password, 'groups_id': [(4, store_emp_group.id)]})

            if not self.user_id:
                raise UserError(f"Employee {full_name} has no linked User (user_id).")

            mail_values = {
                'subject': f"Your Employee Account is Ready – {full_name}",
                'email_to': self.email_id,
                'email_from': self.create_uid.email,
                'email_cc': self.create_uid.email,
                'body_html': f"""
                    <p>Dear <b>{full_name}</b>,</p>

                    <p>We are pleased to inform you that your employee account has been successfully created.</p>

                    <p>Please log in to the Employee Portal to complete your profile, accept the Terms & Conditions, and upload all required documents.</p>

                    <p>
                        Once your profile is fully completed and all T&Cs are accepted, kindly click the 
                        <b>'Request Store Access'</b> button to proceed with your onboarding.
                    </p>

                    <p><b>Login Details:</b><br/>
                    <p>Login link: <a href="{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}">
                    {self.env['ir.config_parameter'].sudo().get_param('web.base.url')}</a></p>
                    Username: {self.user_id.login}<br/>
                    Password: {password}</p>
                    <br/>
                    
                    <p>
                        <b>NOTE:</b> This email is auto-generated. Please do not reply to this email.
                        If you have any questions, please contact your DM.
                    </p><br/>
                    
                    <p>Best regards,<br/>
                    Admin Team</p>
                """,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.sudo().send()

            self.application_state = 'notify_employee'

    # def notify_employee(self):
    #     if not self.tz:
    #         raise ValidationError("Please select a timezone for the employee to create a user.")

    #     # Check if a user with the same email/login exists
    #     res_user_id = self.env['res.users'].search([('login', '=', self.email_id)], limit=1)
    #     if res_user_id:
    #         # Skip this employee, log or print info
    #         _logger.info(f"Skipping employee {self.name} because user with email {self.email_id} already exists.")
    #         return False  # Skip and move to the next record

    #     # Prepare email and full name
    #     email = (self.email_id or '').lower()
    #     parts = [self.first_name or '', self.middle_name or '', self.last_name or '']
    #     full_name = " ".join(p for p in parts if p).strip()

    #     vals = {
    #         'name': full_name,
    #         'login': email,
    #         'tz': self.tz,
    #     }

    #     # Create user
    #     user_id = self.env['res.users'].sudo().create(vals)
    #     if user_id:
    #         self.user_id = user_id
    #         # Assign store access rights in user
    #         self.assign_higher_access_role_group_to_user()
    #         # Assign sub employees once user_id is created
    #         self.env.user.sudo().compute_domain_employee_ids()

    #         # Update partner email
    #         if self.user_id.partner_id:
    #             self.user_id.partner_id.sudo().write({'email': self.email_id})
        
    #     return True

    def action_create_active_employee(self):
        if self._context.get("active_model") == "hr.employee":
            domain = [("id", "in", self._context.get("active_ids", []))]
        employee_ids = self.env["hr.employee"].search(domain)
        for employee in employee_ids:
            if employee and not employee.user_id:
                employee.notify_employee()


# class HrEmployeePublic(models.Model):
#   _inherit = "hr.employee.public"

#   per_hr_wage = fields.Float(string="Per Hour Wage")


class Resource(models.Model):
  _inherit = "resource.resource"

  name = fields.Char(string="Name",required=False)
