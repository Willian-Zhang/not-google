Number.prototype.numberWithCommas = function(){
    return this.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

$(document).ready(()=>{
    const socket = io('/search');
    $('#search-form').submit(function(){
        socket.emit('search', $(this).find('input').val().trim());
        return false;
    });
    let metaInfoElement = $('#info spam');
    let searchResultElement = $('#slots');
    
    var slotTemplate = $(`
    <div class="slot">
        <h3 class="slot-title"><a href="...">Title</a></h3>
        <div class="slot-url">http://</div>
        <div class="slot-snippet">Content</div>
        <div class="slot-infos">BM2.5: </div>
    </div>`)

    socket.on('search result', function(result){
        console.log(result);
        metaInfoElement.text(`${result.meta.results.numberWithCommas()} results. (${result.meta.time.toPrecision(3)} seconds)`);
        searchResultElement.empty();
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
                element.find('.slot-infos').text(`Language: ${slotItem.lang}, BM2.5: ${0}`);
                return element;
            });
            searchResultElement.append(elements)
        }else{
            searchResultElement.append($(`<div class="no-result"></div>`)
                .text(`Your search - ${""} - did not match any documents.`));
        }
             
    });
    
    socket.on('reloaded', function(msg){
        metaInfoElement.text('Reloaded');
    });
})