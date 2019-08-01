/* ========================================================================
 * Copyright (c) 2018 Oleksandr Komarov, Modool (https://modool.pro)
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 * ======================================================================== */
odoo.define('pos_blackbox_ua.blackbox_ua', function (require) {
"use strict";


var ajax = require('web.ajax');
var core = require('web.core');
var mixins = require('web.mixins');
var Session = require('web.Session');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var Widget = require('web.Widget');
var web_client = require('web.web_client');

var _t = core._t;

/* The method: var ProxyDevice = require('point_of_sale.devices').ProxyDevice;
*   don't work because this module upload only in POS view
*   OWN POS PROXY
*/

// this object interfaces with the local proxy to communicate to the various hardware devices
// connected to the Point of Sale. As the communication only goes from the POS to the proxy,
// methods are used both to signal an event, and to fetch information.

var ProxyDevice  = core.Class.extend(mixins.PropertiesMixin, {
    init: function(parent,options){
        mixins.PropertiesMixin.init.call(this);
        var self = this;
        this.setParent(parent);
        options = options || {};
        // TODO remove unused attributes

        this.weighing = false;
        this.debug_weight = 0;
        this.use_debug_weight = false;

        this.paying = false;
        this.default_payment_status = {
            status: 'waiting',
            message: '',
            payment_method: undefined,
            receipt_client: undefined,
            receipt_shop:   undefined,
        };
        this.custom_payment_status = this.default_payment_status;

        this.receipt_queue = [];

        this.notifications = {};
        this.bypass_proxy = false;

        this.connection = null;
        this.host       = '';
        this.keptalive  = false;

        this.set('status',{});

        this.set_connection_status('disconnected');

        this.on('change:status',this,function(eh,status){
            status = status.newValue;
//            if(status.status === 'connected'){
//                self.print_receipt();
//            }
        });

        this.posbox_supports_display = false;
        this.config = {
            proxy_ip: false, // TODO get data from POS settings
        };

//        window.hw_proxy = this;
    },
    set_connection_status: function(status,drivers){
        var oldstatus = this.get('status');
        var newstatus = {};
        newstatus.status = status;
        newstatus.drivers = status === 'disconnected' ? {} : oldstatus.drivers;
        newstatus.drivers = drivers ? drivers : newstatus.drivers;
        if (odoo.debug){
            console.log('connection status: ', newstatus);
//            web_client.do_notify(_t('Fiscal Box status: ') + newstatus.status, '');
        };
        this.set('status',newstatus);
    },
    disconnect: function(){
       if (odoo.debug){
           console.warn('Disconnect...');
       };
       if(this.get('status').status !== 'disconnected'){
            this.connection.destroy();
            this.set_connection_status('disconnected');
        }
    },
    destroy: function(){
        if (odoo.debug){
            console.warn('This is DESTROYER');
        };
        // FIXME, should wait for flushing, return a deferred to indicate successfull destruction
        // this.flush();
        this.proxy.close();
    },

    // connects to the specified url
    connect: function(url){
        if (odoo.debug){
            console.warn('Connect to url: ',url);
        };
        var self = this;
        this.connection = new Session(undefined,url, { use_cors: true});
        this.host   = url;
        this.set_connection_status('connecting',{});

        return this.message('handshake').then(function(response){
                if(response){
                    self.set_connection_status('connected');
                    localStorage.hw_proxy_url = url;
//                    self.keepalive();
                }else{
                    self.set_connection_status('disconnected');
                    if (odoo.debug){
                        console.error('Connection refused by the Proxy');
                    };
                }
            },function(){
                self.set_connection_status('disconnected');
                if (odoo.debug){
                    console.error('Could not connect to the Proxy');
                };
            });
    },


    // find a proxy and connects to it. for options see find_proxy
    //   - force_ip : only try to connect to the specified ip.
    //   - port: what port to listen to (default 8069)
    //   - progress(fac) : callback for search progress ( fac in [0,1] )
    autoconnect: function(options){
        var self = this;
        this.set_connection_status('connecting',{});
        var found_url = new $.Deferred();
        var success = new $.Deferred();

        if ( options.force_ip ){
            // if the ip is forced by server config, bailout on fail
            found_url = this.try_hard_to_connect(options.force_ip, options);
        }else if( localStorage.hw_proxy_url ){
            // try harder when we remember a good proxy url
            found_url = this.try_hard_to_connect(localStorage.hw_proxy_url, options)
                .then(null,function(){
                    return self.find_proxy(options);
                });
        }else{
            // just find something quick
            found_url = this.find_proxy(options);
        }

        success = found_url.then(function(url){
                return self.connect(url);
            });

        success.fail(function(){
            self.set_connection_status('disconnected');
        });

        return success;
    },

    // returns as a deferred a valid host url that can be used as proxy.
    // options:
    //   - port: what port to listen to (default 8069)
    //   - progress(fac) : callback for search progress ( fac in [0,1] )
    find_proxy: function(options){
        options = options || {};
        var self  = this;
        var port  = ':' + (options.port || '8069');
        var urls  = [];
        var found = false;
        var parallel = 8;
        var done = new $.Deferred(); // will be resolved with the proxies valid urls
        var threads  = [];
        var progress = 0;


        urls.push('http://localhost'+port);
        for(var i = 0; i < 256; i++){
            urls.push('http://192.168.0.'+i+port);
            urls.push('http://192.168.1.'+i+port);
            urls.push('http://10.0.0.'+i+port);
        }

        var prog_inc = 1/urls.length;

        function update_progress(){
            progress = found ? 1 : progress + prog_inc;
            if(options.progress){
                options.progress(progress);
            }
        }

        function thread(done){
            var url = urls.shift();

            done = done || new $.Deferred();

            if( !url || found || !self.searching_for_proxy ){
                done.resolve();
                return done;
            }

            $.ajax({
                    url: url + '/hw_proxy/hello',
                    method: 'GET',
                    timeout: 400,
                }).done(function(){
                    found = true;
                    update_progress();
                    done.resolve(url);
                })
                .fail(function(){
                    update_progress();
                    thread(done);
                });

            return done;
        }

        this.searching_for_proxy = true;

        var len  = Math.min(parallel,urls.length);
        for(i = 0; i < len; i++){
            threads.push(thread());
        }

        $.when.apply($,threads).then(function(){
            var urls = [];
            for(var i = 0; i < arguments.length; i++){
                if(arguments[i]){
                    urls.push(arguments[i]);
                }
            }
            done.resolve(urls[0]);
        });

        return done;
    },


    connect_to_proxy: function(){
        var self = this;
        var  done = new $.Deferred();
        this.autoconnect({
                force_ip: self.config.proxy_ip || undefined,
            }).always(function(){
                done.resolve();
            });
        return done;
    },

    message : function(name,params){
        if (odoo.debug){
           console.warn('message: ', name, params);
        };
        var callbacks = this.notifications[name] || [];
        for(var i = 0; i < callbacks.length; i++){
            if (odoo.debug){
                console.warn('message > callbacks');
            };
            callbacks[i](params);
        }
        if(this.get('status').status !== 'disconnected'){
            if (odoo.debug){
                console.warn('message >>> /hw_proxy/' + name, params || {});
            };
            return this.connection.rpc('/hw_proxy/' + name, params || {});
        }else{
            return (new $.Deferred()).reject();
        }
    },


    // try several time to connect to a known proxy url
    try_hard_to_connect: function(url,options){
        options   = options || {};
        var port  = ':' + (options.port || '8069');

        this.set_connection_status('connecting');

        if(url.indexOf('//') < 0){
            url = 'http://'+url;
        }

        if(url.indexOf(':',5) < 0){
            url = url+port;
        }

        // try real hard to connect to url, with a 1sec timeout and up to 'retries' retries
        function try_real_hard_to_connect(url, retries, done){

            done = done || new $.Deferred();

            console.error('Message : ', + JSON.stringify({
                url: url + '/hw_proxy/hello',
                method: 'GET',
                timeout: 1000,  // FIXME the 'timeout' is not work!
            }));
            $.ajax({
                url: url + '/hw_proxy/hello',
                method: 'GET',
                timeout: 1000,  // FIXME the 'timeout' is not work!
            })
            .done(function(){
                console.error('Message done to ' + url);
                done.resolve(url);
            })
            .fail(function(){
                console.error('Message fail');
                if(retries > 0){
                    try_real_hard_to_connect(url,retries-1,done);
                }else{
                    done.reject();
                }
            });
            return done;
        }

        return try_real_hard_to_connect(url,3);
    },

    // asks the proxy to log some information, as with the debug.log you can provide several arguments.
    log: function(){
        return this.message('log',{'arguments': _.toArray(arguments)});
    },

});


///**
// * Include the FormController and BasicModel to update the datapoint on the
// * model when a message is posted.
// */
//FormController.include({
//    custom_events: _.extend({}, FormController.prototype.custom_events, {
//        'o_fiscal_ua_cash_in': '_fiscal_ua_cash_in',
//        '_fiscal_ua_cash_in': '_fiscal_ua_cash_in',
//        o_fiscal_ua_cash_in: '_fiscal_ua_cash_in',
//    }),
//    events:  _.extend({}, FormController.prototype.events, {
//        'click .o_fiscal_ua_cash_in': '_fiscal_ua_cash_in',
//    }),
//
//    /**
//     * @private
//     * @param {OdooEvent} event
//     * @param {string} event.data.id datapointID
//     * @param {integer[]} event.data.msgIDs list of message ids
//     */
//    _fiscal_ua_cash_in: function (event) {
//        var amount = this.model.get(this.handle).data.amount;
//        if (amount <= 0){
//            alert(_.str.sprintf('Error. Amount have to be >=0. But he is: %.2f', amount));
//            return;
//        };
//        // WARNING: this is cross-domain request!
//        console.warn('Start Cash IN', event);
//        var proxy = new ProxyDevice(this);              // used to communicate to the hardware devices via a local proxy
//        proxy.connect_to_proxy().then(function(){
//            proxy.message('cash_in', {cash_in_sum: amount}).then(function(result){
//                alert('ok - cash_in');
//                console.warn('Message result: ', result);
//            }, function(result){ //failed to read weight
//                alert('Message error. result: ' + JSON.stringify(result));
//                console.error('Message error. result: ', result);
//            });
//            proxy.disconnect();
//        });
//    },
//});

//var CashIn2 = Widget.extend({
////    className: "o_fiscal_ua_cash_in",
//
//    custom_events: {
//        'o_fiscal_ua_cash_in': 'o_fiscal_ua_cash_in'
//    },
//    events:{
////        'click .oe_dashboard_column .oe_fold': '_onFoldClick',
////        'click .oe_dashboard_link_change_layout': '_onChangeLayout',
////        'click .oe_dashboard_column .oe_close': '_onCloseAction',
//        'click .o_fiscal_ua_cash_in': 'o_fiscal_ua_cash_in',
//        'click button': 'o_fiscal_ua_cash_in',
//        '.o_fiscal_ua_cash_in': 'o_fiscal_ua_cash_in',
//        'o_fiscal_ua_cash_in': 'o_fiscal_ua_cash_in',
//    },
//
//    init: function(parent, action) {
//        alert('CashIn2 init');
//        this.actionManager = parent;
//        this.action = action;
//        this.domain = [];
//        return this._super.apply(this, arguments);
//    },
////    start: function () {
////        this.counter = new Counter(this);
////        var def = this.counter.appendTo(this.$el);
////        return $.when(def, this._super.apply(this, arguments);
////    },
//    do_show: function() {
//        alert('CashIn2 do_show');
//        this._super();
////        this.update_cp();
//    },
//    renderButtons: function() {
//        alert('CashIn2 renderButtons');
//    },
//    o_fiscal_ua_cash_in: function(event) {
//        alert('F!!!!!!!!!!!!!1');
//        // do something with event.data.val
//    },
//});
//core.action_registry.add("blackbox_ua_cashin2", CashIn2);


/**
 * Client action to Fiscal Printer UA CashIn.
 */
function CashIn(parent, action, options) {
    var action_context = action.context;
    var operation = action_context.operation;

    // WARNING: this is cross-domain request!
    var proxy = new ProxyDevice(this);              // used to communicate to the hardware devices via a local proxy
    proxy.connect_to_proxy().then(function(){
        console.warn('Start operation: ' + operation, action_context);
        if (operation == 'cash_in'){
            var amount = action_context.sum_amount;
            var active_ids = action_context.active_ids;
            //**************************************************************************************
            //I know, this is ugly. FIXME if you can.
            var new_cont = action_context;
            var modal_f = parent.dialog_widget;
            // change active_model 'cash.box.in' to 'pos.session'.
            new_cont.active_model = modal_f.env.context.active_model;
            new_cont.active_id = modal_f.env.context.active_id;
            new_cont.active_ids = modal_f.env.context.active_ids;
            //**************************************************************************************
            if (amount <= 0){
                alert(_.str.sprintf('Error. Amount have to be >=0. But he is: %.2f', amount));
                return;
            };
            proxy.message('cash_in', {cash_in_sum: amount}).then(function(result){
                console.warn('Message result: ', result);
                if (result.status == 'success'){
                    web_client.do_notify(_t('Ok. Fiscal Cash In: +') + amount, '', true);
                    parent._rpc({
                        model: 'cash.box.in',
                        method: 'run',
                        args: [active_ids, new_cont],
                    }).then(function (result) {
                        web_client.do_notify(_t('Ok. Odoo Cash In: +') + amount, '', true);
                        parent.dialog.destroy();
                    }).fail(function () {
                        web_client.do_notify(_t('Error recording Cash In to Odoo!'),'', true);
                    });
                    //parent.trigger_up('button_clicked', {
                    //    attrs: {special: 'save'},
                    //    //record: self.state,
                    //});
                }else{
                    web_client.do_notify(_t('Error Fiscal Cash In: +') + amount, result.message, true);
                };
            }, function(result){ //failed to read weight
                console.error(_t('Error Cash In. Check BlackBox: connection and power on.'), JSON.stringify(result));
                parent.do_warn(_t('Error Cash In. Check BlackBox: connection and power on.'), JSON.stringify(result));
            });
        }else if(operation == 'cash_out'){
            var amount = action_context.sum_amount;
            var active_ids = action_context.active_ids;
            //**************************************************************************************
            //I know, this is ugly. FIXME if you can.
            var new_cont = action_context;
            var modal_f = parent.dialog_widget;
            // change active_model 'cash.box.in' to 'pos.session'.
            new_cont.active_model = modal_f.env.context.active_model;
            new_cont.active_id = modal_f.env.context.active_id;
            new_cont.active_ids = modal_f.env.context.active_ids;
            //**************************************************************************************
            proxy.message('cash_out', {cash_in_sum: amount}).then(function(result){
                console.warn('Message result: ', result);
                if (result.status == 'success'){
                    web_client.do_notify(_t('Ok. Fiscal Cash Out: -') + amount, '', true);
                    parent._rpc({
                        model: 'cash.box.out',
                        method: 'run',
                        args: [active_ids, new_cont],
                    }).then(function (result) {
                        web_client.do_notify(_t('Ok. Odoo Cash Out: -') + amount, '', true);
                        parent.dialog.destroy();
                    }).fail(function () {
                        web_client.do_notify(_t('Error recording Cash Out to Odoo!'),'', true);
                    });
                }else{
                    web_client.do_notify(_t('Error Fiscal Cash Out: -') + amount, result.message, true);
                };
            }, function(result){ //failed to do it
                console.error(_t('Error Cash Out. Check BlackBox: connection and power on.'), JSON.stringify(result));
                parent.do_warn(_t('Error Cash Out. Check BlackBox: connection and power on.'), JSON.stringify(result));
            });
        }else if(operation == 'z_report'){
            proxy.message('print_ZReport').then(function(result){
                console.warn('Message result: ', result);
                if (result.status == 'success'){
                    web_client.do_notify(_t('Ok. Z report'), '', true);
                }else{
                    web_client.do_notify(_t('Error Z report'), result.message, true);
                };
            }, function(result){ //failed to do it
                console.error(_t('Error Z report. Check Box UA: connection and power on.'), JSON.stringify(result));
                parent.do_warn(_t('Error Z report. Check Box UA: connection and power on.'), JSON.stringify(result));
            });
        }else if(operation == 'x_report'){
            proxy.message('print_x_report').then(function(result){
                console.warn('Message result: ', result);
                if (result.status == 'success'){
                    web_client.do_notify(_t('Ok. X report'), '', true);
                }else{
                    web_client.do_notify(_t('Error X report'), result.message, true);
                };
            }, function(result){ //failed to do it
                console.error(_t('Error X report. Check Box UA: connection and power on.'), JSON.stringify(result));
                parent.do_warn(_t('Error X report. Check Box UA: connection and power on.'), JSON.stringify(result));
            });
        }else if(operation == 'null_receipt'){
            proxy.message('print_0_receipt').then(function(result){
                console.warn('Message result: ', result);
                if (result.status == 'success'){
                    web_client.do_notify(_t('Ok. Null receipt'), '', true);
                }else{
                    web_client.do_notify(_t('Error Null receipt'), result.message, true);
                };
            }, function(result){ //failed to do it
                console.error(_t('Error Null receipt. Check Box UA: connection and power on.'), JSON.stringify(result));
                parent.do_warn(_t('Error Null receipt. Check Box UA: connection and power on.'), JSON.stringify(result));
            });
        }else if(operation == 'disable_fiscal_receipt'){
            // TODO mode this operation to debug menu
            proxy.message('disable_fiscal_receipt').then(function(result){
                console.warn('Message result: ', result);
                if (result.status == 'success'){
                    web_client.do_notify(_t('Ok. "Disabling opened fiscal receipt" added to Task Queue'), '', true);
                }else{
                    web_client.do_notify(_t('Error disabling opened fiscal receipt'), result.message, true);
                };
            });
        };
        proxy.disconnect();
    });
};

core.action_registry.add("blackbox_ua_cashin", CashIn);


});
