function showFlashMessage(message, type = 'warning', timeout = 2500, autoDismiss=true) {
    const $alert = $('<div>', {
        class: `alert alert-${type}`,
        role: 'alert'
    });

    const $closeBtn = $('<button>', {
        type: 'button',
        class: 'btn-close',
        'data-bs-dismiss': 'alert',
        'aria-label': 'Close'
    });

    $alert.append(document.createTextNode(message));
    $alert.append($closeBtn);

    $('.update-toast').append($alert);

    if(autoDismiss) {
        setTimeout(() => {
            $alert.fadeOut('slow', function () {
                $(this).remove();
            });
        }, timeout);
    }
}

function formatDate(value) {
    if (!value) return "";

    // sqlite stores utc without TZ info
    // tell JS explicity to interpret it as UTC
    // if not it would assume the string itself is in local time
    const utcString = value.replace(" ", "T") + "Z";
    const dt = new Date(utcString);

    return dt.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short"
    });
}


function getLocaleInfoHTML() {
    const locale = navigator.language;
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;

    const tzAbbr = new Intl.DateTimeFormat(locale, {
        timeZoneName: 'short'
    })
    .formatToParts(new Date())
    .find(p => p.type === 'timeZoneName')?.value;

    const localeName = getHumanLocaleName(locale);

    const message = `
        Your browser language is set to <b>${localeName}</b> <br/>
        Dates and times are displayed using <b>${tz} (${tzAbbr})</b>
    `;

    return message;
}

function getHumanLocaleName(locale) {
    const [language, region] = locale.split('-');

    const langNames = new Intl.DisplayNames([locale], { type: 'language' });
    const regionNames = new Intl.DisplayNames([locale], { type: 'region' });

    const languageName = langNames.of(language);
    const regionName = region ? regionNames.of(region) : '';

    return regionName
        ? `${languageName} (${regionName})`
        : languageName;
}
