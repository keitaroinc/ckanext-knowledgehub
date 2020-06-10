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