/**
 * JavaScript module for managing the user notifications.
 */
ckan.module('user-profile', function($){
    'use strict';
    $(function(){
        $('.notifications-button').click(function(){
            var notifications = []
            if ($(this).attr('marked')){
                return
            }
            $(this).attr('marked', true);
            $('.notification-item').each(function(_, itm){
                console.log('Notification ->', $(itm).attr('id'));
                notifications.push($(itm).attr('id'))
            })

            if (notifications.length){
                $.ajax('/api/3/action/notifications_read', {
                    type: 'POST',
                    data: JSON.stringify({
                        notifications: notifications,
                    }),
                    dataType: 'json',
                })
            }
        });
    });
});