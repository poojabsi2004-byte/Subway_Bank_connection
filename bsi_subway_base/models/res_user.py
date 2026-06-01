# -*- coding: utf-8 -*-
from odoo import api, models, fields,_

class ResUsers(models.Model):
    _inherit = "res.users"

    domain_employee_ids = fields.Many2many("hr.employee", string="Attendance Employees")

    # Added this method to convert email in lower while login from website
    @classmethod
    def authenticate(cls, db, credential, user_agent_env=None):
        if isinstance(credential, dict) and credential.get("login"):
            credential['login'] = credential['login'].strip().lower()
        return super().authenticate(db, credential, user_agent_env)

    # RM - 6 Aug [ADD] user wise att record rule
    def compute_domain_employee_ids(self):
        user_ids = self.env["res.users"].search([])
        for rec in user_ids:
        # for rec in self:
            employee_list = []
            if rec.has_group('hr_attendance.group_hr_attendance_manager') and rec.has_group('bsi_subway_base.store_owner') or rec.has_group('bsi_subway_base.store_admin'):
                employee_ids = self.env['hr.employee'].search([])
                rec.domain_employee_ids = employee_ids.ids
            else:
                if rec.employee_id and rec.employee_id.employee_access_ids:
                    # Case: There is no separation based on store employees; currently, it only considers
                    # employees without store restrictions (if the same employee is assigned to two different stores).
                    for access_line in rec.employee_id.employee_access_ids:
                        if access_line.access_role == 'district_manager':
                            if rec.employee_id.id not in employee_list:    #Own
                                employee_list.append(rec.employee_id.id)
                            for access_store in access_line.store_ids:
                                if access_store.store_manager_ids:    #Store managers
                                    for store_manager in access_store.store_manager_ids:
                                        if store_manager.id not in employee_list:
                                            employee_list.append(store_manager.id)
                                if access_store.employee_ids:    #Employees
                                    for store_emp in access_store.employee_ids:
                                        if store_emp.id not in employee_list:
                                            employee_list.append(store_emp.id)
                        elif access_line.access_role == 'store_manager':
                            if rec.employee_id.id not in employee_list:    #Own
                                employee_list.append(rec.employee_id.id)
                            for access_store in access_line.store_ids:
                                if access_store.employee_ids:    #Employees
                                    for store_emp in access_store.employee_ids:
                                        if store_emp.id not in employee_list:
                                            employee_list.append(store_emp.id)
                        elif access_line.access_role == 'employee':
                            if rec.employee_id.id not in employee_list:    #Own
                                employee_list.append(rec.employee_id.id)
                rec.domain_employee_ids = employee_list

    # @api.depends("employee_id", "employee_id.employee_access_ids")
    # def compute_domain_employee_ids(self):
    #     print("_________________11111_____PASSSSSSSSS____")
    #     for rec in self:
    #         employee_list = []
    #         print("_______employee_list_________________",employee_list)
    #         # Owner & Admin → full access
    #         if rec.has_group('hr_attendance.group_hr_attendance_manager') and rec.has_group('bsi_subway_base.store_owner') or rec.has_group('bsi_subway_base.store_admin'):
            
    #         # if rec.has_group("hr_attendance.group_hr_attendance_manager") or \
    #         #    rec.has_group("bsi_subway_base.store_owner") or \
    #         #    rec.has_group("bsi_subway_base.store_admin"):
    #             employee_list = self.env["hr.employee"].search([]).ids
    #             print("______employee_list____employee_list__",employee_list)

    #         elif rec.employee_id and rec.employee_id.employee_access_ids:
    #             for access_line in rec.employee_id.employee_access_ids:
    #                 if access_line.access_role == "district_manager":
    #                     # Own record
    #                     employee_list.append(rec.employee_id.id)
    #                     print("_________DM_______",employee_list)

    #                     # Store Managers + Employees
    #                     for access_store in access_line.store_ids:
    #                         employee_list += access_store.store_manager_ids.ids
    #                         employee_list += access_store.employee_ids.ids
    #                         print("_________SM + EMP_______",employee_list)

    #                 elif access_line.access_role == "store_manager":
    #                     # Own record
    #                     employee_list.append(rec.employee_id.id)
    #                     print("_________SM_______",employee_list)

    #                     # Store Employees
    #                     for access_store in access_line.store_ids:
    #                         employee_list += access_store.employee_ids.ids
    #                         print("_________EMP_______",employee_list)

    #                 elif access_line.access_role == "employee":
    #                     # Only Own
    #                     employee_list.append(rec.employee_id.id)
    #                     print("_________EMP_______",employee_list)

    #         rec.domain_employee_ids = list(set(employee_list))

# RM - 11 FEB [ADD] Store manager and District manager to employee password change.(Base method Override)
class ChangePasswordWizard(models.TransientModel):
    _inherit = "change.password.wizard"

    def change_password_button(self):
        self.ensure_one()
        self.user_ids.sudo().change_password_button()
        if self.env.user in self.user_ids.user_id:
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        return {'type': 'ir.actions.act_window_close'}
