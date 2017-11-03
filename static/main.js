Number.prototype.numberWithCommas = function(){
    return this.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

$(document).ready(()=>{
    const socket = io('/search');

    let metaInfoElement = $('#info spam');
    let searchResultElement = $('#slots');
    var currentKeyword = "";
    let search = function(keyword, page){
        document.title = `${keyword} - Not Google`;
        window.history.pushState(keyword, document.title, `/?s=${encodeURI(keyword)}&p=${page}`);
        socket.emit('search', {keyword: keyword, page: page});
        metaInfoElement.text('Searching...');
        searchResultElement.empty();
        currentKeyword = keyword;
    };

    let load_page = function(){
        try {
            let locationSearch = JSON.parse('{"' + decodeURI(location.search.substring(1)).replace(/"/g, '\\"').replace(/&/g, '","').replace(/=/g,'":"') + '"}');
            if(locationSearch.s){
                // this is okey
                page = 0
                if (locationSearch.p){
                    page = locationSearch.p
                }
                $('#search-form input').val(locationSearch.s);
                if(socket.connected){
                    search(locationSearch.s, page);
                }else{
                    socket.once('connect', function(){
                        setTimeout(()=>{
                            search(locationSearch.s, page);
                        }, 100);
                    })
                }
            }
        } catch (error) {
            console.warn(error)
        }
    };
    load_page();

        let previousTemplete = $(`
        <li class="page-item">
        <a class="page-link" href="#" aria-label="Previous">
            <span aria-hidden="true">&laquo;</span>
            <span class="sr-only">Previous</span>
        </a>
        </li>`);
        let nextTemplete = $(`
        <li class="page-item">
            <a class="page-link" href="#" aria-label="Next">
            <span aria-hidden="true">&raquo;</span>
            <span class="sr-only">Next</span>
            </a>
        </li>`);
        let pageItemElement = $(`<li class="page-item"><a class="page-link" href="#">a</a></li>`);
        let pageItemElementCurrent = $(`
        <li class="page-item active">
            <span class="page-link">
            2
            
            </span>
        </li>`);
    let paginationElement = $("#pagination");
    let setCurrentPage = function(page, pages){
        var clickEventHandler = function(event){
            search(currentKeyword, event.data);
        }
        paginationElement.empty()
        let previous = previousTemplete.clone()
        if(page == 0){
            previous.addClass("disabled");
        }else{
            previous.click(page - 1, clickEventHandler);
        }
        paginationElement.append(previous);
        
        let startPage = page > 5 ? page - 5 : 0;
        let endPage = page < pages - 5 - 1? page + 5 : pages - 1;
        for (var index = startPage; index < endPage; index++) {
            if(index==page){
                var ele = pageItemElementCurrent.clone()
                ele.find("span").text(index+1);
                ele.append(`<span class="sr-only">(current)</span>`)
            }else{
                var ele = pageItemElement.clone();
                ele.find("a").text(index+1);
                ele.click(index, clickEventHandler)
            }
            paginationElement.append(ele);
        }
        if(startPage>0){
            var ele = pageItemElement.clone();
            ele.find("a").text(1);
            ele.click(0, clickEventHandler)
            paginationElement.prepend(ele);
        }

        let next = nextTemplete.clone()
        if(page == pages-1){
            next.addClass("disabled");
        }else{
            next.click(page + 1, clickEventHandler)
        }
        paginationElement.append(next);
    };

    window.onpopstate = function(e){
        if(e.state){
            load_page();
        }
    };

    $('#search-form').submit(function(){
        let input = $(this).find('input');
        search($(this).find('input').val().trim(), 0);
        input.blur()
        return false;
    });
    
    var slotTemplate = $(`
    <div class="slot">
        <h3 class="slot-title shrink-line"><a href="...">Title</a></h3>
        <div class="slot-url shrink-line">http://</div>
        <div class="slot-snippet ">Content</div>
        <div class="slot-infos">BM25: </div>
    </div>`);

    socket.on('search result', function(result){
        console.log(result);
        metaInfoElement.text(`${result.meta.results.numberWithCommas()} results. (${result.meta.time.toPrecision(3)} seconds)`);
        if(result.meta.results > 0){
            elements = result.results.map(slotItem => {
                let element = slotTemplate.clone()
                element.find('.slot-title a').text(slotItem.title);
                element.find('.slot-title a').attr('href', slotItem.url);
                try {
                    element.find('.slot-url').text(decodeURI(slotItem.url));
                } catch (error) {
                    element.find('.slot-url').text(slotItem.url);
                }
                element.find('.slot-infos').text(`Language: ${slotItem.lang}, BM25: ${slotItem.bm25.toPrecision(3)}, Total: ${slotItem.count}`);
                snippetElement = element.find('.slot-snippet')
                snippetElement.empty()
                
                snippetLengthMinusOne = slotItem.snippets.length - 1;
                slotItem.snippets.map((snippet, i) =>{
                    snippetElement.append(document.createTextNode(snippet));
                    if(i < snippetLengthMinusOne){
                        snippetElement.append("<br />");
                    }
                });
                if (slotItem.snippets.length > 1){
                    snippetElement.addClass("shrink-line");
                }
                if(result.meta.keywords){
                    snippetElement.highlight(result.meta.keywords);
                }
                return element;
            });
            searchResultElement.append(elements)
        }else{
            searchResultElement.append($(`<div class="big-info"></div>`)
                .text(`Your search - ${result.meta.query} - did not match any documents.`));
        }
        setCurrentPage(result.meta.page, result.meta.pages)
    });
    
    socket.on('reloaded', function(msg){
        metaInfoElement.text('Reloaded');
    });

    socket.on('simple info', function(msg){
        metaInfoElement.text(msg);
    });

    socket.on('multiple info', function(msgs){
        metaInfoElement.text('Done');
        msgs.map(info => {
            searchResultElement.append($(`<div class="big-info"></div>`).text(info));
        });
    });
});
