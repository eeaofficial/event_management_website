$(document).ready(function() {

    /* -----------------------------
       REGISTER FORM SUBMISSION
    ----------------------------- */

    function makeLinksClickable(text) {
        const urlPattern = /(https?:\/\/[^\s]+)/g;
        return text.replace(urlPattern, function(url) {
            return `<a href="${url}" target="_blank" style="color:yellow;font-weight:bold;">
                        ${url}
                    </a>`;
        });
    }

    $('#modal-form').on('submit', function(event) {
        event.preventDefault();

        $('#msg').html('Please Wait!!!');

        $.ajax({
            url: REGISTER_URL,
            type: 'POST',
            data: {
                "id": $('#event-id').val(),
                "reg1": $('#reg1').val(),
                "reg2": $('#reg2').val(),
                "reg3": $('#reg3').val(),
                "reg4": $('#reg4').val(),
                "reg5": $('#reg5').val(),
                "type": EVENT_CATEGORY
            }
        })
        .done(function(data) {

            $('#register-modal').modal('hide');

            if (data.error) {

                $('#msg').html(data.error);
                $('#register-modal').modal('hide');
                $('#alert-modal').modal('show');

            } else {

                let content = PARTICIPANT_INFO && PARTICIPANT_INFO.trim() !== "" 
                    ? makeLinksClickable(PARTICIPANT_INFO).replace(/\n/g, "<br>")
                    : data.success;

                $('#msg').html(`
                    <h5 style="color:yellow;">Registration Successful 🎉</h5>
                    <hr/>
                    ${content}
                `);

                $('#alert-modal').modal('show');
            }

        })
        .fail(function() {
            $('#register-modal').modal('hide');
            $('#msg').html("Something went wrong. Please try again.");
            $('#alert-modal').modal('show');
        });
    });


    /* -----------------------------
       DELETE TEAM MEMBER ROW
    ----------------------------- */

    $("body").on("click", "#DeleteRow", function () {
        $(this).parents("#row").remove();
    });


    /* -----------------------------
       ADD EVENT FORM SUBMISSION
       (Corrected Selector + Single Handler)
    ----------------------------- */

    $('#add-event-form').on('submit', function(event) {
        event.preventDefault();

        var formData = $(this).serialize();
        var url = $(this).attr('action');

        $.ajax({
            url: url,
            type: 'POST',
            data: formData,
            success: function(response) {
                alert('Form data submitted successfully!');
                // do something with response
            },
            error: function(jqXHR, textStatus) {
                alert(textStatus);
                // handle error
            }
        });
    });

});