    $(function() {
        $('#theme').change(function() {
            populateSubThemes();
        })
    });

    function populateSubThemes() {
        var api = {
        get: function(action, params, async) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            params = $.param(params);
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            if (!async) {
                $.ajaxSetup({
                    async: false
                });
            }
            return $.getJSON(url);
        } };

        theme = $('#theme :selected').text();
        theme2 = $('#theme').val();
        api.get('sub_theme_list', {'theme': theme2}).done(function (data){
        $('#sub_theme').empty();
        for(i = 0; i < data.result.data.length; ++i)
        {
            $('#sub_theme').append(new Option(data.result.data[i].title, data.result.data[i].id));
        }

        });
    };
    // </script>

