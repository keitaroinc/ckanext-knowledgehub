/*
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

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