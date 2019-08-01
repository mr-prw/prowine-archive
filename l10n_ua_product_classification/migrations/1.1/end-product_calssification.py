from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, dict())
    for item in env['product.product'].search([]):
        if item.ukt_zed:
            uktzed_id = env['product.classification'].search([('name', '=', item.ukt_zed.strip())], limit=1)
            item.ukt_zed_id = uktzed_id
