/* ========================================================================
 * Copyright (c) 2018 Oleksandr Komarov, Modool (https://modool.pro)
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 * ======================================================================== */
odoo.define('pos_blackbox_ua.chrome', function (require) {
"use strict";

/* This module redefine data, which POSTed to BlockBox via ProxyStatusWidget.set_smart_status
 In Odoo CE used 'status.drivers.escpos' but in Fiscal UA used 'status.drivers.fiscalpos'.
 */


var chrome = require('point_of_sale.chrome');

var core = require('web.core');

var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

/* --------- The Proxy Status --------- */

// Displays the status of the hardware proxy
// (connected, disconnected, errors ... )

chrome.ProxyStatusWidget.include({
    set_smart_status: function(status){
        if(status.status === 'connected'){
            var warning = false;
            var msg = '';
            if(this.pos.config.iface_scan_via_proxy){
                var scanner = status.drivers.scanner ? status.drivers.scanner.status : false;
                if( scanner != 'connected' && scanner != 'connecting'){
                    warning = true;
                    msg += _t('Scanner');
                }
            }
            if( this.pos.config.iface_print_via_proxy || 
                this.pos.config.iface_cashdrawer ){
                // redefined this
                var printer = status.drivers.fiscalpos ? status.drivers.fiscalpos.status : false;
                if( printer != 'connected' && printer != 'connecting'){
                    warning = true;
                    msg = msg ? msg + ' & ' : msg;
                    msg += _t('Printer');
                }
            }
            if( this.pos.config.iface_electronic_scale ){
                var scale = status.drivers.scale ? status.drivers.scale.status : false;
                if( scale != 'connected' && scale != 'connecting' ){
                    warning = true;
                    msg = msg ? msg + ' & ' : msg;
                    msg += _t('Scale');
                }
            }

            msg = msg ? msg + ' ' + _t('Offline') : msg;
            this.set_status(warning ? 'warning' : 'connected', msg);
        }else{
            this.set_status(status.status,'');
        }
    },
});


});

