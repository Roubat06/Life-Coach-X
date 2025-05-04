$(document).ready(function () {
    $('#send-button').click(function () {
        const userInput = $('#user-input').val();
        if (!userInput.trim()) return;

        $('#chat').append(`<div><strong>You:</strong> ${userInput}</div>`);
        $('#user-input').val('');
        $('#loading').show();

        $.ajax({
            url: '/chat',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ message: userInput }),

            success: function (response) {
                $('#chat').append(`<div><strong>Bot:</strong> ${response.response}</div>`);

                $('#loading').hide();
                $('#chat').scrollTop($('#chat')[0].scrollHeight);
            },
            error: function (xhr, status, error) {
                $('#chat').append(`<div style="color:red;"><strong>Error:</strong> ${xhr.responseJSON?.error || error}</div>`);
                $('#loading').hide();
            }
        });
    });
});
