
/**
 * Module that handles actions related to likes on posts.
 * 
 * Handles the "Like" and "Remove Like" action on a signle post or on a list of
 * posts on the newsfeed.
 */
ckan.module('likes', function($){
    $(function(){

        /**
         * Calls CKAN API on a specific URL.
         * @param {String} url API action URL 
         * @param {String} ref the ref (ID) of the Post.
         * 
         * @returns a {Promise} of the API call.
         */
        function call_api(url, ref){
            return new Promise(function(resolve, reject){
                $.ajax({
                    url: url,
                    dataType: 'json',
                    method: 'POST',
                    data: {
                        'ref': ref
                    },
                    success: function(){
                        resolve()
                    },
                    error: function(err){
                        reject(err)
                    }
                })
            })
        }
    
        /**
         * Adds a like to the post identified by ref.
         * @param {String} ref the post ID (ref). 
         */
        function like(ref) {
            return call_api('/api/3/action/like_create', ref);
        }

        /**
         * Removes a like from the post identified by ref.
         * @param {String} ref the post ID (ref). 
         */
        function deleteLike(ref){
            return call_api('/api/3/action/like_delete', ref);
        }

        $('[like-ref]').each(function(i, el) {
            var ref = $(el).attr('like-ref');
            $(el).click(function(){

                function addLikeCount(amount) {
                    var likesCount = parseInt($('.likes-count', el).html() || '0') + amount;
                    $('.likes-count', el).html(likesCount);
                }

                function showSpinner() {
                    $('i', el).removeClass('fa-thumbs-o-up').addClass('fa-circle-o-notch', 'fa-spin')
                }

                function clearSpinner() {
                    $('i', el).removeClass('fa-circle-o-notch', 'fa-spin').addClass('fa-thumbs-o-up')
                }

                function showError(msg) {
                    $('.like-action-error', $(el).parent()).html(msg);
                }

                function clearError() {
                    $('.like-action-error', $(el).parent()).html('');
                }

                var isLiked = ($(el).attr('liked') || '').toLowerCase() === 'true';
                function addLike() {
                    clearError()
                    showSpinner()
                    like(ref).then(function(){
                        addLikeCount(1)
                        clearSpinner()
                        $(el).attr('liked', 'true').addClass('likes-active')
                    }).catch(function(){
                        clearSpinner()
                        showError('Something went wrong. Please try again.')
                    });
                }

                function removeLike() {
                    clearError()
                    showSpinner()
                    deleteLike(ref).then(function(){
                        addLikeCount(-1); // decrease likes count
                        clearSpinner()
                        $(el).attr('liked', 'false').removeClass('likes-active')
                    }).catch(function(){
                        clearSpinner()
                        showError('Somehting went wrong. Please try again.')
                    })
                }

                if (isLiked) {
                    removeLike()
                } else {
                    addLike()
                }
            })
        })

    })
});