(function(){
    $(function(){
        var commentTemplate = $('.comment-template').clone();
        var addCommentTemplate = $('.add-comment-template').clone();
        var deletedCommentContentTemplate = $('.comment-deleted-content').clone();
        var propmtTemplate = $('.prompt-template').clone();
        var loaderTemplate = $('.generic-loader').clone()

        var api = {
            getComments: function(ref, page, limit, success, error) {
                $.ajax({
                    'url': '/api/3/action/comments_list',
                    'method': 'POST',
                    'data': {
                        'page': page,
                        'limit': limit,
                        'ref': ref,
                    },
                    'dataType': 'json',
                    'success': function(resp){
                        if (success){
                            success(resp.result)
                        }
                    },
                    'error': error
                })
            },
            getCommentThread: function(ref, commentId, success, error) {
                $.ajax({
                    'url': '/api/3/action/comments_thread_show',
                    'method': 'POST',
                    'data': {
                        'ref': ref,
                        'thread_id': commentId
                    },
                    'dataType': 'json',
                    'success': function(resp){
                        if(success){
                            success(resp.result)
                        }
                    },
                    'error': error
                })
            },
            addComment: function(data, success, error){
                $.ajax({
                    'url': '/api/3/action/comment_create',
                    'method': 'POST',
                    'data': {
                        'ref': data.ref,
                        'content': data.content,
                        'reply_to': data.replyTo
                    },
                    'dataType': 'json',
                    'success': function(resp){
                        if(success){
                            success(resp.result)
                        }
                    },
                    'error': error
                })
            },
            deleteComment: function(commentId, success, error){
                $.ajax({
                    'url': '/api/3/action/comment_delete',
                    'method': 'POST',
                    'data': {
                        'id': commentId
                    },
                    'dataType': 'json',
                    'success': function(resp){
                        if(success){
                            success(resp)
                        }
                    },
                    'error': error
                })
            },
            updateComment: function(commentId, content, success, error) {
                $.ajax({
                    'url': '/api/3/action/comment_update',
                    'method': 'POST',
                    'data': {
                        'id': commentId,
                        'content': content,
                    },
                    'dataType': 'json',
                    'success': function(resp){
                        if(success){
                            success(resp.result)
                        }
                    },
                    'error': error
                })
            }
        }

        function addCommentBox(options){
            var el = addCommentTemplate.clone();
            options.content = (options.content || '').trim();
            
            if (!options.showAvatar) {
                $('img.gravatar', el).remove();
            }

            $('.comment-content', el).val(options.content);
            if (options.okLabel) {
                $('.action-ok', el).html(options.okLabel);
            }

            $('.action-ok', el).click(function(){
                if(options.onOk){
                    var content = $('.comment-content', el).val();
                    options.onOk(content, el);
                }
            });
            if (options.showCancel) {
                $('.action-cancel', el).click(function(){
                    if(options.onCancel){
                        options.onCancel(el);
                    }
                });
            }else{
                $('.action-cancel', el).remove();
            }
            return el;
        }

        function showModalPrompt(title, content, onOk) {
            var el = $(propmtTemplate).clone();
            $('.title-content', el).html(title);
            $('.modal-body p', el).html(content);
            $('.action-ok', el).click(onOk);
            $(document.body).append(el);
            var modal = $(el).modal({
                show: true
            })
            return modal;
        }

        function newLoader(){
            var el = $(loaderTemplate).clone()
            return el;
        }

        function addComment(ctx, comment, currentUser, prepend) {
            var commentEl = $('#comment-' + comment.id, ctx);
            var shouldAppend = true;
            if (commentEl.length) {
                shouldAppend = false;
            }
            var replies = comment.replies || []
            if(shouldAppend) {
                commentEl = commentTemplate.clone();
            }else{
                commentEl = commentEl[0];
            }
            
            
            var gravatarEl = $('.gravatar', commentEl)[0];
            var usernameEl = $('.comment-info .comment-user .user-name', commentEl)[0];
            var timeEl = $('.comment-info .comment-time', commentEl)[0];
            var contentEl = $('.comment-content', commentEl)[0];
            var commentActionsEl = $('.comment-info .comment-actions', commentEl)[0];
            var actionReplyEl = $('.action-reply', commentEl)[0];
            var showMoreRepliesEl = $('.action-show-more-replies', commentEl)[0];
            var replyBoxContainer = $('.reply-box-container', commentEl)[0];

            // populate data
            $(gravatarEl).attr('src', '//gravatar.com/avatar/' + comment.user.email_hash + '?s=32&d=identicon')
            $(usernameEl).html(comment.user.display_name)
            $(timeEl).html(comment.human_timestamp).attr('title', comment.created_at);
            if(comment.deleted){
                $(contentEl).html('').append($(deletedCommentContentTemplate).clone())
                $(commentActionsEl).hide();
            } else {
                $(contentEl).html(comment.display_content)
            }
            $(commentEl).attr('id', 'comment-' + comment.id)

            // show/hide parts
            if(currentUser != comment.user.id){
                $(commentActionsEl).hide()
            }
            $(showMoreRepliesEl).hide();
            if(!comment.thread_id) {
                // top level comment
                if (comment.thread_replies_count > replies.length) {
                    var repliesLeft = comment.thread_replies_count - replies.length;
                    $(showMoreRepliesEl).html('<i class="fa fa-caret-down"></i> Show ' + repliesLeft + ' more replies')
                    $(showMoreRepliesEl).show()
                }
            }

            // setup actions

            // reply to comment
            $(actionReplyEl).click(function(){
                $(actionReplyEl).hide()
                var replyTextBox = addCommentBox({
                    showAvatar: true,
                    showCancel: true,
                    okLabel: 'Reply',
                    onOk: function(content){
                        content = content.trim();
                        if (content === ''){
                            return
                        }
                        var loader = newLoader()
                        $('.status', replyTextBox).html('')
                        $('.status', replyTextBox).append(loader)

                        api.addComment({
                            content: content,
                            ref: comment.ref,
                            replyTo: comment.id,
                        }, function(reply){
                            addComment(commentEl, reply, currentUser, true)
                            $(replyTextBox).remove()
                            $(actionReplyEl).show();
                        }, function(err){
                            $(loader).remove()
                            $('.status', replyTextBox).html('Something went wrong. Try again...')
                        })
                    },
                    onCancel: function(){
                        $(replyTextBox).remove()
                        $(actionReplyEl).show();
                    }
                })
                $(replyBoxContainer).append(replyTextBox)
            })

            $(showMoreRepliesEl).click(function(){
                var loader = newLoader()
                $(showMoreRepliesEl).parent().prepend(loader);
                api.getCommentThread(comment.ref, comment.id, function(replies){
                    replies.forEach(function(reply){
                        addComment(commentEl, reply, currentUser)
                    })
                    $(showMoreRepliesEl).hide()
                    $(loader).remove()
                }, function(err){
                    $(loader).remove()
                })
            })

            $('.action-delete', commentActionsEl).click(function(){
                var modal = showModalPrompt('Delete', 'Are you sure you want to delete this comment?', function(){
                    var loader = newLoader()
                    $('.status', modal).html('').append(loader);
                    api.deleteComment(comment.id, function(){
                        $(contentEl).html('').append($(deletedCommentContentTemplate).clone())
                        $(modal).modal('hide');
                        $(commentActionsEl).hide();
                    }, function(){
                        $(loader).remove()
                        $('.status', modal).html('Something went wrong. Please try again...')
                    })
                })
            })

            $('.action-edit', commentActionsEl).click(function(){
                var contentBox = addCommentBox({
                    showAvatar: false,
                    showCancel: true,
                    okLabel: 'Update',
                    content: comment.content,
                    onOk: function(content){
                        content = (content || '').trim()
                        if (!content) {
                            return
                        }
                        var loader = newLoader()
                        $('.status', contentBox).html('').append(loader)
                        api.updateComment(comment.id, content, function(result){
                            $(contentBox).remove();
                            $(contentEl).html(result.display_content);
                            comment.content = result.content
                        }, function(err){
                            $(loader).remove()
                            $('.status', contentBox).html('Something went wrong. Please try again...')
                        })
                    },
                    onCancel: function(){
                        $(contentBox).remove();
                        $(contentEl).html(comment.content);
                    }
                });
                $(contentEl).html('').append(contentBox);
            })

            // add replies, if any
            replies.forEach(function(reply){
                addComment(commentEl, reply, currentUser);
            });

            if (shouldAppend){
                if (prepend){
                    $($('.comments-container', ctx)[0]).prepend(commentEl);
                } else {
                    $($('.comments-container', ctx)[0]).append(commentEl);
                }
            }

            return commentEl;
        }
        

        function showComments(el) {
            var ref = $(el).attr('show-comments-for')
            var currentUser = $(el).attr('user')
            var loaderEl = $('.loading-comments')[0];
            
            el.shouldScroll = true;
            $(window).scroll(function(){
                if ($(document).height() - $(this).height() == $(this).scrollTop()) {
                    if(el.shouldScroll){
                        el.shouldScroll = false;
                        nextPage(function(){
                            setTimeout(function(){
                                el.shouldScroll = true;
                            }, 2000)
                        })
                    }
                }
            });

            var page = 1;
            var hasMoreComments = true;
            var pageLoading = false;

            var nextPage = function(onComplete){
                onComplete = onComplete || function (){}
                if(!hasMoreComments || pageLoading){
                    pageLoading = false
                    onComplete()
                    return
                }
                pageLoading = true
                $(loaderEl).show();
                api.getComments(ref, page, 20, function(result){
                    $(loaderEl).hide();
                    if (result.count === 0) {
                        $('.no-comments', el).show();
                    }
                    if (result.results && result.results.length === 0) {
                        hasMoreComments = false;
                        onComplete()
                        return;
                    }
                    page++;
                    result.results.forEach(function(comment) {
                        addComment(el, comment, currentUser);
                    })
                    pageLoading = false
                    onComplete()
                }, function(){
                    $(loaderEl).hide();
                    pageLoading = false
                    onComplete()
                });
            }

            var addNewCommentBox = addCommentBox({
                showAvatar: true,
                showCancel: false,
                content: '',
                onOk: function(content) {
                    content = (content || '').trim()
                    if (!content) {
                        return
                    }
                    var loader = newLoader()
                    $('.status', addNewCommentBox).html('')
                    $('.status', addNewCommentBox).append(loader)
                    api.addComment({
                        content: content,
                        ref: ref,
                    }, function(comment){
                        addComment(el, comment, currentUser, true);
                        $('.comment-content', addNewCommentBox).val('')
                        $(loader).remove()
                        $('.no-comments', el).remove();
                    }, function(err){
                        $(loader).remove()
                        $('.status', addNewCommentBox).html('Somethig went wrong. Try again...')
                    })
                }
            });
            $('.add-new-comment', el).append(addNewCommentBox);
            nextPage();

        }

        $('[show-comments-for]').each(function(i, el){
            showComments(el);
        });

    })
})()