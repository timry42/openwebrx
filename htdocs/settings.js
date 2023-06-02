$(function(){
    $('.map-input').mapInput();
    $('.imageupload').imageUpload();
    $('.bookmarks').bookmarktable();
    $('.wsjt-decoding-depths').wsjtDecodingDepthsInput();
    $('#waterfall_scheme').waterfallDropdown();
    $('#rf_gain').gainInput();
    $('.optional-section').optionalSection();
    $('#scheduler').schedulerInput();
    $('.exponential-input').exponentialInput();
    $('.device-log-messages').logMessages();
    $('.profile-tabs').draggableList({
        dataType: 'application/x-profile',
        itemSelector: '.profile',
        idProperty: 'profile-id',
        performMove: function(profileId, index) {
            var url = $('.profile-tabs .device a').attr('href');
            return $.ajax(url + '/moveprofile', {
                data: JSON.stringify({profile_id: profileId, index: index}),
                contentType: 'application/json',
                method: 'POST'
            });
        }
    });
});