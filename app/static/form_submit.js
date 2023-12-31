$(document).ready(function() {
    $('#modal-form').on('submit', function(event) {
        event.preventDefault();
        $('#msg').html('Please Wait!!!');
        $.ajax({
            data:{
                "id":$('#event-id').html(),
                "reg1":$('#reg1').val(),
                "reg2":$('#reg2').val(),
                "reg3":$('#reg3').val(),
                "reg4":$('#reg4').val(),
                "reg5":$('#reg5').val(),
                'type':'{{event.category}}'
            },
            type: 'POST',
            url: '/register'
        })
        .done(function(data){
            if(data.error) {
                $('#msg').html(data.error);
                $('#register-modal').modal('hide');
                $('#alert-modal').modal('show');
                // console.log(data.error);
            }
            else {
                $('#msg').html(data.success);
                $('#register-modal').modal('hide');
                $('#alert-modal').modal('show');
            }
        });
    });

    // $("#rowAdder").click(function () {
    //     newRowAdd =
    //     '<div id="row"> <div class="input-group m-3">' +
    //     '<div class="input-group-prepend">' +
    //     '<button class="btn btn-danger" id="DeleteRow" type="button">' +
    //     '<i class="bi bi-trash"></i> Delete</button> </div>' +
    //     '<input type="text" class="form-control m-input"> </div> </div>';

    //     $('#modal-form').append(newRowAdd);
    // });

    $("body").on("click", "#DeleteRow", function () {
        $(this).parents("#row").remove();
    });


    $("add-event-form").on('submit', function(event) {
        event.preventDefault();

        var formData = $(this).serialize();
        var url = $('input[type="submit"]').data('url');

        $.ajax({
            url: url, // URL to submit form data
            type: 'POST',
            data: formData,
            success: function(response) {
                alert('Form data submitted successfully!');
                // do something with response
            },
            error: function(jqXHR, textStatus, errorThrown) {
                // console.log(textStatus, errorThrown);
                alert(textStatus);
                // handle error
            }
        });
    });

    $("add-event-form").on('submit', function(event) {
        event.preventDefault();

        var formData = $(this).serialize();
        var url = $('input[type="submit"]').data('url');

        $.ajax({
            url: url, // URL to submit form data
            type: 'POST',
            data: formData,
            success: function(response) {
                alert('Form data submitted successfully!');
                // do something with response
            },
            error: function(jqXHR, textStatus, errorThrown) {
                // console.log(textStatus, errorThrown);
                alert(textStatus);
                // handle error
            }
        });
    });

});