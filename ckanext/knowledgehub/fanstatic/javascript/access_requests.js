(function (_, $) {

    function confimationModal(selector, onYes, onNo) {
        var modal = $(selector);
        modal.modal({
            'show': true
        })
        $('#btnYes', modal).on('click', function(){
            if(onYes){
                onYes()
            }
            modal.modal('hide');
        })
        $('#btnNo', modal).on('click', function(){
            if(onNo){
                onNo()
            }
            modal.modal('hide');
        })
    }

    $(function(){
        var table = $('#access_requests').DataTable({
            paging: true,
            search: false,
            serverSide: true,
            ordering: false,
            iDisplayLength: 25,
            columns: [{
                data: "requested"
            }, {
                data: "entity_type",
            }, {
                data: "requested_by"
            }, {
                data: 'requested_at'
            }, {
                data: "actions"
            }],
            ajax: {
                url: '/api/3/action/access_request_list',
                method: 'POST',
                data: function(data) {
                    return {
                        'page': data.start/data.length + 1,
                        'limit': data.length,
                        'search': data.search ? data.search.value : ''
                    };
                },
                dataSrc: function(data) {
                    var results = data.result.results.map(function(record) {
                        record.requested = [
                            '<a href="', record.entity_link, '">',
                            record.entity_title, '</a>'].join('');
                        record.requested_by = record.user.full_name
                        record.actions = [
                            '<div class="btn-group pull-right">',
                                '<button class="btn btn-primary action-access-request-grant" ',
                                'href="', record.grant_url ,'">',
                                    '<i class="fa fa-plus"></i>',
                                    _('Grant Access'),
                                '</button>',
                                '<button class="btn btn-danger action-access-request-decline"',
                                'href="', record.decline_url ,'">',
                                    '<i class="fa fa-trash"></i>',
                                    _('Decline'),
                                '</button>',
                            '</div>'
                        ].join('')
                        record.requested_at = moment(record.created_at).format('lll')
                        return record;
                    });
                    return results;
                }
            }
        });
        table.on('xhr', function(ev, settings, resp){
            if(resp.result) {
                resp.recordsTotal = resp.result.count;
                resp.recordsFiltered = resp.result.count;
            }
        })
        $(document).on('click', '.action-access-request-grant', function(){
            confimationModal('#modalGrant', function(){
                window.location = $(this).attr('href');
            }.bind(this))
        })
        $(document).on('click', '.action-access-request-decline', function(){
            confimationModal('#modalDecline', function(){
                window.location = $(this).attr('href');
            }.bind(this))
        })
    });
})(ckan.i18n.ngettext, $);