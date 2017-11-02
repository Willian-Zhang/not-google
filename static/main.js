Number.prototype.numberWithCommas = function(){
    return this.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

$(document).ready(()=>{
    const socket = io('/search');

    let metaInfoElement = $('#info spam');
    let searchResultElement = $('#slots');
    let search = function(keyword){
        document.title = `${keyword} - Not Google`;
        window.history.pushState(keyword, document.title, `/?s=${encodeURIComponent(keyword)}`);
        socket.emit('search', keyword);
        metaInfoElement.text('Searching...');
        searchResultElement.empty();
    };

    let load_page = function(){
        try {
            let locationSearch = JSON.parse('{"' + decodeURI(location.search.substring(1)).replace(/"/g, '\\"').replace(/&/g, '","').replace(/=/g,'":"') + '"}');
            if(locationSearch.s){
                // this is okey
                $('#search-form input').val(locationSearch.s);
                if(socket.connected){
                    search(locationSearch.s);
                }else{
                    socket.once('connect', function(){
                        setTimeout(()=>{
                            search(locationSearch.s);
                        }, 100);
                    })
                }
            }
        } catch (error) {
            console.warn(error)
        }
    };
    load_page();
    window.onpopstate = function(e){
        if(e.state){
            load_page();
        }
    };

    $('#search-form').submit(function(){
        let input = $(this).find('input');
        search($(this).find('input').val().trim());
        input.blur()
        return false;
    });
    
    var slotTemplate = $(`
    <div class="slot">
        <h3 class="slot-title shrink-line"><a href="...">Title</a></h3>
        <div class="slot-url shrink-line">http://</div>
        <div class="slot-snippet ">Content</div>
        <div class="slot-infos">BM2.5: </div>
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
                element.find('.slot-infos').text(`Language: ${slotItem.lang}, BM2.5: ${slotItem.bm25.toPrecision(3)}, Total: ${slotItem.count}`);
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
