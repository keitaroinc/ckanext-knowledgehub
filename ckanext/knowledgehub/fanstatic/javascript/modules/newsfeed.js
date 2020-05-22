ckan.module('newsfeed', function($){

    var InfiniteScroll = function() {
        this.scroll = function() {
            return new Promise(function(resolve) {
                if(this.onScroll) {
                    this.onScroll().then(function(){
                        resolve();
                    }).catch(function(err){
                        resolve();
                    });
                    return
                }
                resolve();
            }.bind(this));
        }
    }

    var infiniteScroll = new InfiniteScroll();
    var shouldScroll = true;
    $(function(){
        $(window).scroll(function(){
            if ($(document).height() - $(this).height() == $(this).scrollTop()) {
                if(shouldScroll){
                    shouldScroll = false;
                    infiniteScroll.scroll().then(function(){
                        setTimeout(function(){
                            shouldScroll = true;
                        }, 2000);
                    })
                }
            }
        });
    })

    var Pagination = function(el) {
        this.el = el;
        this.currentPage = 1;

        var intOrDefault = function(str, defaultVal) {
            try {
                return parseInt(str)
            } catch (e) {
                return defaultVal
            }
        }

        this.getPaginationInfo = function(){
            var itemsPerPage = $(el).attr('pagination-per-page')
            var currentPage = $(el).attr('pagination-page')
            var url = $(el).attr('pagination-url')
            var totalItems = $(el).attr('pagination-total')

            this.currentPage = intOrDefault(currentPage, 1)
            this.itemsPerPage = intOrDefault(itemsPerPage, 20)
            this.totalItems = intOrDefault(totalItems, undefined)
            this.url = url ? url.trim() : ''
            
        }

        this.getPaginationInfo()

        this.getNextPage = function(){
            return new Promise(function(resolve, reject) {
                if(!this.url){
                    reject('no URL endpoint for pagination specified')
                    return
                }

                if(this.totalItems !== undefined && this.totalItems >= 0){
                    if(this.currentPage*this.itemsPerPage >= this.totalItems) {
                        reject('no more data to fetch')
                        return
                    }
                }
                
                var url = [
                    this.url,
                    'page=' + (this.currentPage + 1),
                    'limit=' + this.itemsPerPage
                ].join('&')
                $.get(url, 'html').done(function(resp){
                    $(this.el).append(resp)
                    this.currentPage += 1
                    resolve()
                }.bind(this)).fail(function(err){
                    reject(err)
                });
            }.bind(this));
        }
        
    }

    $(function(){
        var el = $('[pagination-container]');
        if (el.length) {
            var pagination = new Pagination(el);
            infiniteScroll.onScroll = function(){
                return pagination.getNextPage();
            }
        }
    });
});