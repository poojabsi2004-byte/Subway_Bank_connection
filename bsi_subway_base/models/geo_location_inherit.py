# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError

class EmpGeoLocation(models.Model):
    _inherit = "emp.geo_location"
    _description = "Emp Geo Location"

    store_id = fields.Many2one('store.store', string="Store", required=True, tracking=True)
    store_number = fields.Integer(string="Store No", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'store_id' in vals:
                store_id = self.env['store.store'].browse(vals['store_id'])
                vals['store_number'] = store_id.store_number
        res_ids = super(EmpGeoLocation, self).create(vals_list)
        # for rec in res_ids:
        #     store_id.write({'geo_location_id': rec.id})
        return res_ids

    def write(self, vals):
        if 'store_id' in vals:
            store_id = self.env['store.store'].browse(vals['store_id'])
            vals.update({
                'store_number': store_id.store_number
            })
            # store_id.write({'geo_location_id': self.id})
        return super(EmpGeoLocation, self).write(vals)

    @api.constrains('store_id')
    def _restrict_duplicate_store_allocation(self):
        for record in self:
            if record and record.store_id:
                duplicate_rec = self.env['emp.geo_location'].search([('store_id','=', record.store_id.id)])
                if len(duplicate_rec) > 1:
                    error_msg = "You already have assigned store '" + str(record.store_id.name) + "' to another location."
                    raise ValidationError(error_msg)
