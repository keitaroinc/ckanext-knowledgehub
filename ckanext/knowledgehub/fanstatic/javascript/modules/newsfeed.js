ckan.module('newsfeed', function($){

    var shouldScroll = true;

    $(function(){
        $(window).scroll(function(){
            if ($(document).height() - $(this).height() == $(this).scrollTop()) {
                if(shouldScroll){
                    console.log('Scroll to bottom')
                    shouldScroll = false;
                    setTimeout(function(){
                        shouldScroll = true;
                    }, 1300)
                }
            }
        });
    })
});