/*
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

ckan.module('mentions', function($){

    function query(q, done) {

       $.ajax({
           url: '/api/3/action/query_mentions',
           data: {
               q: q
           },
           dataType: 'json',
           method: 'GET',
           success: function(resp) {
               done(resp.result)
           }
       })
    }

    function activateMentions(el) {
        $(el).suggest('@', {
            data: query,
            map: function(record) {
                var markup = ['<div class="mention-entry">']
                if (record.image) {
                    markup.push('<img class="mention-image" src="' + record.image + '"></img>')
                }
                markup.push('<div class="mention-label">' + record.label + '</div>')
                markup.push('</div>')
                return {
                    text: markup.join(''),
                    value: record.value
                }
            }
        })
    }

    $(function(){
        var buildMentions = function(ctx) {
            $('[mentions]', $(ctx)).each(function(i, el){
                if(el.mentionsActivated) {
                    return
                }
                el.mentionsActivated = true
                activateMentions(el);
            });
        }
        buildMentions(document)

        // watch for new DOM elements inserted with attribute mentions
        var observer = new MutationObserver(function(mutations) {
            for (var i = 0; i < mutations.length; i++) {
                var mutation = mutations[i];
                if (mutation.type == 'childList') {
                    buildMentions(mutation.target)
                }
            }
        })

        observer.observe(document, {childList: true, subtree: true})
    })
});