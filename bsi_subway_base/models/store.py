# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
# from datetime import datetime, time
# from odoo.exceptions import ValidationError, AccessError, UserError


class StoreStore(models.Model):
    _name = "store.store"
    _description = "Stores"
    _inherit = ["mail.thread","mail.activity.mixin"]

    name = fields.Char(string="Store", required='1', tracking=True)
    store_number = fields.Integer(string="Store No", required='1', tracking=True)
    name_with_number = fields.Char(string="Store with No", compute="compute_name_with_number")
    geo_location_id = fields.Many2one('emp.geo_location', string="Geo Location", compute="compute_geo_location_id")


    active = fields.Boolean(string="Active", default=True)
    currency_id = fields.Many2one('res.currency', string="Currency",default=lambda self: self.env.user.company_id.currency_id,readonly=True)
    total_hourly_wage = fields.Float(string="Total Hourly Wage",compute="_compute_total_hourly_wage",store=True,tracking=True)

    employee_ids = fields.Many2many('hr.employee',
        'rel_employee_store',
        'store_id',
        'employee_id', string="Employees", readonly=True)
    store_manager_ids = fields.Many2many('hr.employee',
        'rel_store_manager_store',
        'store_id',
        'employee_id', string="Store Managers", readonly=True)
    district_manager_ids = fields.Many2many('hr.employee',
        'rel_district_manager_store',
        'store_id',
        'employee_id', string="District Managers", readonly=True)
    store_line_ids = fields.One2many('store.scheduling', 'store_id', string="Store Lines")

    #GS JAN30 2025 To exclude botspot store in mail
    is_exclude_store = fields.Boolean(string="Exclude Store in email?")

########################### Cash Deposit Reminder [START]###############################################################################

    recipient_user_ids = fields.Many2many(
        'hr.employee',
        'rel_store_recipient_store',
        'store_id',
        'employee_id',
        string="Recipient Users",
        tracking=True,
        readonly=False
    )
    wednesday = fields.Boolean(string="Wednesday",tracking=True)
    thursday = fields.Boolean(string="Thursday",tracking=True)
    friday = fields.Boolean(string="Friday",tracking=True)
    saturday = fields.Boolean(string="Saturday",tracking=True)
    sunday = fields.Boolean(string="Sunday",tracking=True)
    monday = fields.Boolean(string="Monday",tracking=True)
    tuesday = fields.Boolean(string="Tuesday",tracking=True)

    def _update_recipient_users(self):
        records = self.search([])
        for rec in records:
            managers = rec.store_manager_ids | rec.district_manager_ids
            rec.recipient_user_ids = managers | rec.recipient_user_ids

    @api.model
    def create(self, vals):
        record = super(StoreStore, self).create(vals)
        if vals.get("recipient_user_ids"):
            employees = self.env['hr.employee'].browse(vals['recipient_user_ids'][0][2])
            names = ", ".join(employees.mapped("display_name"))
            record.message_post(
                body=_("<b>Recipient Users:</b><br/><b>From</b> : None<br/><b>To</b> : %s") % names
            )
        return record

    def write(self, vals):
        if "recipient_user_ids" in vals:
            for rec in self:
                old_employees = rec.recipient_user_ids
                old_names = ", ".join(old_employees.mapped("display_name")) or "None"

                result = super(StoreStore, rec).write(vals)

                new_employees = rec.recipient_user_ids
                new_names = ", ".join(new_employees.mapped("display_name")) or "None"

                if old_names != new_names:
                    rec.message_post(
                        body=_("<b>Recipient Users:</b><br/><b>From</b> : %s<br/><b>To</b> : %s") % (old_names, new_names)
                    )

                return result
        return super(StoreStore, self).write(vals)

########################### Cash Deposit Reminder [END]###############################################################################


    @api.depends('employee_ids','store_manager_ids')
    def _compute_total_hourly_wage(self):
        for rec in self:
            total_hourly_wage = 0.0
            if rec.store_manager_ids:
                for store_mngr in rec.store_manager_ids:
                    if store_mngr.per_hr_wage:
                        total_hourly_wage += store_mngr.per_hr_wage
            if rec.employee_ids:
                for store_emp in rec.employee_ids:
                    if store_emp.per_hr_wage:
                        total_hourly_wage += store_emp.per_hr_wage
            rec.total_hourly_wage = total_hourly_wage

    ##MP IF want to show name with number at many2one selction
    ## Use this in xml to implement it on specific view: context="{'show_full_name': 1}"
    # def name_get(self):
    #     if self._context.get('show_full_name'):
    #         res = []
    #         for rec in self:
    #             name = rec.name
    #             if rec.name and rec.store_number:
    #                 name = '%s (%s)' % (name, rec.store_number)
    #             res.append((rec.id, name))
    #         return res
    #     return super(StoreStore, self).name_get()

    @api.depends('name','store_number')
    def compute_name_with_number(self):
        for rec in self:
            name_with_number = ''
            if rec.name:
                name_with_number = rec.name
            if rec.store_number:
                name_with_number += ' (' + str(rec.store_number) + ')'
            rec.name_with_number = name_with_number

    #MP TODO: need to store this compute field. #Ignored CASE: Multi locations at single store
    def compute_geo_location_id(self):
        for rec in self:
            location_ids = self.env['emp.geo_location'].search([('store_id', '=', rec.id)])
            if location_ids:
                for location in location_ids:
                    rec.geo_location_id = location.id
            else:
                rec.geo_location_id = False

    #MP - Query: Need to review the 'compute_domain_employee_ids' function, as it is executing for
    # all users instead of a specific single user.
    #GS 10AUG24 to Update Employee For User to see attendance
    def update_employee_attendance(self):
        for rec in self:
            user = self.env.user
            user.compute_domain_employee_ids()

    # # store_employee_onboard_ids = fields.One2many('employee.onboard','store_id',string="Employees")
    # store_manager_id = fields.Many2one('hr.employee', string="Manager",tracking=True, domain="[('type_of_employee','=','store_manager')]")
    # district_manager_id = fields.Many2one('hr.employee', string="District Manager",tracking=True, domain="[('type_of_employee','=','district_manager')]")

    # allowed_scheduling_hours = fields.Float(string="Allowed Scheduling Hours")
    # grace = fields.Float(string="Grace (%)")
    # # JS 29APR24 CODE NOT USED FOR FURTHER COMPARISION INSTEAD ADDED IN STORE SCHEDULING START
    # # min_allow_hr_range = fields.Float(string="Min Allowed Hours Range", compute="_compute_min_allow_hr_range", store="1")
    # # max_allow_hr_range = fields.Float(string="Max Allowed Hours Range", compute="_compute_max_allow_hr_range", store="1")
    # # payroll_expense = fields.Float(string="Payroll Expense", compute="_compute_payroll_expenses", store="1")
    # min_allow_hr_range = fields.Float(string="Min Allowed Hours Range")
    # max_allow_hr_range = fields.Float(string="Max Allowed Hours Range")
    # payroll_expense = fields.Float(string="Payroll Expense")
    # # JS 29APR24 CODE NOT USED FOR FURTHER COMPARISION INSTEAD ADDED IN STORE SCHEDULING END 

    # payroll_expense_in_percentage = fields.Float(string="Payroll Expense in (%)")
    # actual_payroll_debit = fields.Float(string="Actual Payroll Debit")
    # payroll_taxes = fields.Float(string="Payroll Taxes")

    # allowed_food_expenses = fields.Float(string="Allowed Food Expenses")
    # food_grace = fields.Float(string="Grace (%)")
    # # JS 29APR24 CODE NOT USED FOR FURTHER COMPARISION INSTEAD ADDED IN STORE SCHEDULING START
    # # min_allow_expense_range = fields.Float(string="Min Allowed Food Expenses",compute="_compute_min_allow_expense_range")
    # # max_allow_expense_range = fields.Float(string="Max Allowed Food Expenses",compute="_compute_max_allow_expense_range")
    # min_allow_expense_range = fields.Float(string="Min Allowed Food Expenses")
    # max_allow_expense_range = fields.Float(string="Max Allowed Food Expenses")
    # # JS 29APR24 CODE NOT USED FOR FURTHER COMPARISION INSTEAD ADDED IN STORE SCHEDULING END 

    # food_expense = fields.Float(string="Food Expenses")
    # total_expenses = fields.Float(string="Total Expenses")
    # food_expense_in_percentage = fields.Float(string="Food Expenses in (%)")
    # food_cost_bank = fields.Float(string="Food Cost Bank")


    # # JUN 12 Geo Location added
    '''JS 29APR24 CODE NOT USED FOR FURTHER COMPARISION INSTEAD ADDED IN STORE SCHEDULING START 

    @api.depends('allowed_scheduling_hours','total_hourly_wage')
    def _compute_payroll_expenses(self):
        for rec in self:
            payroll_expense = 0.0
            if rec.allowed_scheduling_hours and rec.total_hourly_wage:
                payroll_expense = rec.allowed_scheduling_hours*rec.total_hourly_wage
            rec.payroll_expense = payroll_expense

    @api.depends('allowed_scheduling_hours','grace')
    def _compute_min_allow_hr_range(self):
        for rec in self:
            min_allow_hr_range = 0.0
            if rec.allowed_scheduling_hours and rec.grace:
                min_allow_hr_range = rec.allowed_scheduling_hours - ((rec.grace*rec.allowed_scheduling_hours)/100)
            rec.min_allow_hr_range = min_allow_hr_range

    @api.depends('allowed_scheduling_hours','grace')
    def _compute_max_allow_hr_range(self):
        for rec in self:
            max_allow_hr_range = 0.0
            if rec.allowed_scheduling_hours and rec.grace:
                max_allow_hr_range = rec.allowed_scheduling_hours + ((rec.grace*rec.allowed_scheduling_hours)/100)
            rec.max_allow_hr_range = max_allow_hr_range

    @api.depends('allowed_food_expenses','food_grace')
    def _compute_min_allow_expense_range(self):
        for rec in self:
            min_allow_expense_range = 0.0
            if rec.allowed_food_expenses and rec.food_grace:
                min_allow_expense_range = rec.allowed_food_expenses - ((rec.food_grace*rec.allowed_food_expenses)/100)
            rec.min_allow_expense_range = min_allow_expense_range

    @api.depends('allowed_food_expenses','food_grace')
    def _compute_max_allow_expense_range(self):
        for rec in self:
            max_allow_expense_range = 0.0
            if rec.allowed_food_expenses and rec.food_grace:
                max_allow_expense_range = rec.allowed_food_expenses + ((rec.food_grace*rec.allowed_food_expenses)/100)
            rec.max_allow_expense_range = max_allow_expense_range
    JS 29APR24 CODE NOT USED FOR FURTHER COMPARISION INSTEAD ADDED IN STORE SCHEDULING END '''
