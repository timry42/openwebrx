$.fn.profileList = function() {
    this.each(function () {
        var $profileList = $(this);
        var $profiles = $profileList.find('.profile');
        $profiles.attr('draggable', 'true');
        $profiles.find('a').attr('draggable', 'false');
        var $profileEl;
        var originalIndex;
        $profileList.on('dragstart', '.profile', function(event){
            $profileEl = $(event.originalEvent.target);
            originalIndex = $profileEl.index();
            event.originalEvent.dataTransfer.effectAllowed = 'move';
            event.originalEvent.dataTransfer.setData('application/x-profile', $profileEl.data('profile-id'));
        }).on('dragenter', function(event) {
            event.preventDefault();
            var $target = $(event.target).closest('.profile');
            if ($profileEl.index() < $target.index()) {
                $profileEl.insertAfter($target);
            } else {
                $profileEl.insertBefore($target);
            }
        }).on('dragover', function(event) {
            event.preventDefault();
        }).on('dragend', function(event) {
            if (event.originalEvent.dataTransfer.dropEffect === 'none') {
                // drag was aborted - restore original position
                $profileEl.remove().insertBefore($profileList.children().eq(originalIndex));
            }
            $profileEl = undefined;
        });
    });
}