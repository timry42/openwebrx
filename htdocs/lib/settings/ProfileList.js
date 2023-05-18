$.fn.profileList = function() {
    var dataType = 'application/x-profile';

    var isValidDrag = function(event) {
        // check and avoid external drags
        if (!event.originalEvent.dataTransfer.types.includes(dataType)) return false;

        var $target = $(event.target).closest('.profile');

        // check if we are a valid drop target
        return !!$target.length;
    }

    this.each(function () {
        var $profileList = $(this);
        var $profiles = $profileList.find('.profile');
        $profiles.attr('draggable', 'true');
        $profiles.find('a').attr('draggable', 'false');
        var $profileEl;
        var originalIndex;
        var $spinner = $('.overlay-spinner');

        var moveProfile = function(profileId, index) {
            var url = $profileList.find('.device a').attr('href');
            return $.ajax(url + '/moveprofile', {
                data: JSON.stringify({profile_id: profileId, index: index}),
                contentType: 'application/json',
                method: 'POST'
            });
        }

        $profileList.on('dragstart', '.profile', function(event){
            $profileEl = $(event.originalEvent.target);
            originalIndex = $profileEl.index();
            event.originalEvent.dataTransfer.effectAllowed = 'move';
            event.originalEvent.dataTransfer.setData(dataType, $profileEl.data('profile-id'));
        }).on('dragenter', function(event) {
            if (!isValidDrag(event)) return;
            event.preventDefault();

            var $target = $(event.target).closest('.profile');
            if ($profileEl.index() < $target.index()) {
                $profileEl.insertAfter($target);
            } else {
                $profileEl.insertBefore($target);
            }
        }).on('dragover', function(event) {
            if (!isValidDrag(event)) return;
            event.preventDefault();
        }).on('drop', function(event) {
            if (!isValidDrag(event)) return;
            var $target = $(event.target).closest('.profile');
            var index = $profileList.find('.profile').index($target);

            $spinner.addClass('d-flex');
            moveProfile(event.originalEvent.dataTransfer.getData(dataType), index).done(function() {
                // done
            }).fail(function() {
                // backend reported error, restore original position
                $profileEl.remove().insertBefore($profileList.children().eq(originalIndex));
            }).always(function() {
                $profileEl = undefined;
                $spinner.removeClass('d-flex');
            });
        }).on('dragend', '.profile', function(event) {
            if (event.originalEvent.dataTransfer.dropEffect === 'none') {
                // drag was aborted - restore original position
                $profileEl.remove().insertBefore($profileList.children().eq(originalIndex));
            }
        });
    });
}