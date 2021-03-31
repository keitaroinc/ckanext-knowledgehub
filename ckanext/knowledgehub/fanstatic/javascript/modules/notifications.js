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

/**
 * JavaScript module for managing the user notifications.
 */
ckan.module('notifications', function($){
    'use strict';

    var markAsRead = function(notificationId){
        return $.ajax('/api/3/action/notifications_read', {
            type: 'POST',
            data: JSON.stringify({
                notifications: [notificationId],
            }),
            dataType: 'json',
        })
    }

    var decreaseNotificationCount = function() {
        var count = $('.notifications-count').html();
        try {
            count = parseInt(count.trim());
            count--;
            if (count >= 0) {
                $('.notifications-count').html(count)
            }
        }catch (e) {}
    }

    $(function(){
        var itemTemplate = $('.notification-list-item').first().clone();
        var lastId = $('.notification-item').last().attr('id')
        var showMore = function(){
            $.ajax('/api/3/action/notification_list', {
                type: 'POST',
                data: JSON.stringify({
                    limit: 5,
                    last_key: lastId,
                }),
                dataType: 'json',
            }).done(function(resp){
                var result = resp.result;
                $(result.results).each(function(_, notification){
                    var el = itemTemplate.clone();
                    $(el).attr('id', notification.id);
                    $('.notification-title', el).html(notification.title);
                    if(notification.link){
                        $('.notification-title', el).attr('href', notification.link);
                    }
                    $('.notification-content', el).html(notification.description);
                    if (notification.image){
                        $('.notification-image', el).attr('src', notification.image);
                    }else{
                        $('.notification-image', el).hide();
                        $('.notification-image-default', el).show();
                    }
                    
                    $('.notifications-list').append(el);

                    $('.notification-mark-read', el).attr('notification', notification.id);
                    $('.notification-mark-read', el).click(function(ev){
                        ev.stopPropagation();
                        ev.preventDefault();
                        var notificationId = notification.id;
                        markAsRead(notificationId).done(function(){
                            $('#'+notificationId+'.notification-list-item').remove()
                            decreaseNotificationCount()
                            if($('.notification-item').length == 0){
                                showMore()
                            }
                        }.bind(this));
                    }.bind(this));
                    if (notification.image) {
                        $('.notification-icon', el).css('visibility', 'hidden');
                    }else{
                        $('.notification-icon', el).css('visibility', 'visible');
                    }
                    lastId = notification.id;
                }.bind(this));
                if (!result.results.length){
                    $('.item-show-more').remove();
                    return
                }
                
                $('.notification-item').last()[0].scrollIntoView({
                    behavior: 'smooth'
                })
            });
        }

        $('.notification-content, .notification-title').click(function(e){
            e.preventDefault();
            e.stopPropagation();
            var href = $(this).attr('href');
            var notificationId = $(this).attr('notification');
            markAsRead(notificationId).done(function(){
                    setTimeout( function() {
                        window.location = href;
                    }, 500);
            });
        });

        $('.notifications-show-more').click(function(ev){
            ev.stopPropagation();
            ev.preventDefault();
            showMore();
        });

        $('.notification-mark-read').click(function(ev){
            ev.stopPropagation();
            ev.preventDefault();
            var notificationId = $(this).attr('notification');
            markAsRead(notificationId).done(function(){
                if($('.notification-item').length == 1){
                    showMore()
                }
                $('#'+notificationId+'.notification-item').remove()
                decreaseNotificationCount()
            }.bind(this));
        })
        
    });
});