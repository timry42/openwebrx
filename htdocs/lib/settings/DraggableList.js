$.fn.draggableList = function(options) {
    var isValidDrag = function(event) {
        // check and avoid external drags
        if (!event.originalEvent.dataTransfer.types.includes(options.dataType)) return false;

        var $target = $(event.target).closest(options.itemSelector);

        // check if we are a valid drop target
        return !!$target.length;
    }

    this.each(function () {
        var $list = $(this);
        var $items = $list.find(options.itemSelector);
        $items.attr('draggable', 'true');
        $items.find('a').attr('draggable', 'false');
        var $draggedElement;
        var originalIndex;
        var $spinner = $('.overlay-spinner');

        $list.on('dragstart', options.itemSelector, function(event){
            $draggedElement = $(event.originalEvent.target);
            originalIndex = $draggedElement.index();
            event.originalEvent.dataTransfer.effectAllowed = 'move';
            event.originalEvent.dataTransfer.setData(options.dataType, $draggedElement.data(options.idProperty));
        }).on('dragenter', function(event) {
            if (!isValidDrag(event)) return;
            event.preventDefault();

            var $target = $(event.target).closest(options.itemSelector);
            if ($draggedElement.index() < $target.index()) {
                $draggedElement.insertAfter($target);
            } else {
                $draggedElement.insertBefore($target);
            }
        }).on('dragover', function(event) {
            if (!isValidDrag(event)) return;
            event.preventDefault();
        }).on('drop', function(event) {
            if (!isValidDrag(event)) return;
            var $target = $(event.target).closest(options.itemSelector);
            var index = $list.find(options.itemSelector).index($target);

            $spinner.addClass('d-flex');
            options.performMove(event.originalEvent.dataTransfer.getData(options.dataType), index).done(function() {
                // done
            }).fail(function() {
                // backend reported error, restore original position
                $draggedElement.remove().insertBefore($list.children().eq(originalIndex));
            }).always(function() {
                $draggedElement = undefined;
                $spinner.removeClass('d-flex');
            });
        }).on('dragend', options.itemSelector, function(event) {
            if (event.originalEvent.dataTransfer.dropEffect === 'none') {
                // drag was aborted - restore original position
                $draggedElement.remove().insertBefore($list.children().eq(originalIndex));
            }
        });
    });
}