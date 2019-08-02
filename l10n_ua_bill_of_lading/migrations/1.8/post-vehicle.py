from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, dict())
    for line in env['stock.picking'].search([]):
        old_vehicle = env['vehicle'].search([('id', '=', line.vehicle_id.id)])
        new_vehicle = env['fleet.vehicle'].search([('license_plate', '=', old_vehicle.vehicle_reg.name)])
        line.fleet_vehicle_id = new_vehicle
