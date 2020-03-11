/**
 * JavaScript module for managing the user notifications.
 */
ckan.module('user-profile', function($){
    'use strict';
    $(function(){
        $('.notifications-button').click(function(){
            var notifications = []
            $('.notification-item').each(function(_, itm){
                console.log('Notification ->', $(itm).attr('id'));
                notifications.push($(itm).attr('id'))
            })

            if (notifications){
                $.post('/api/3/action/notifications_read', {
                    notifications: notifications,
                })
            }
        });
    });
});