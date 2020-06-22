(function($){
    $(function(){
        $('[datepicker]').datetimepicker({
            'format': 'YYYY-MM-DD HH:mm:ss'
        })

        $('#timespan button').click(function(){
            $('input[name="timespan"]').val($(this).attr('timespan'))
        });

        $('button[timespan="custom"]').click(function(el){
            el.preventDefault()
            el.stopPropagation()
            if(!$(this).hasClass('active')) {
                $('#timespan button').removeClass('active')
                $(this).addClass('active')
                $('.custom-timespan').show();
            }
        })
    })
})($)