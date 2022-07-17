

var init = function (textField, searchField, button) {

    ymaps.ready(async function () {
        initMap();

        searchField.onkeyup = async function (event) {
            if (event.key == 'Enter') {
                await processInput(searchField);
            }
        }
        button.onclick = async function () {
            await processInput(searchField);
        }
    });

}

var mapRef;
function initMap() {
    mapRef = new ymaps.Map('map', {
        center: [55.76, 37.64], // Moscow
        zoom: 4
    }, {
        searchControlProvider: 'yandex#search'
    });
}

async function processInput(textField) {
    try {
        await clearMarkers();
        let productName = textField.value;
        let addresses = await getAddresses(productName);
        if (addresses.length == 0) {
            throw 'Ничего не найдено';
        }
        for (const i in addresses) {
            let addressData = addresses[i];
            var izgInfo = `Изготовитель<br />${addressData.il}<br />Адрес: ${addressData.izgotovitelAddress}<br />Организация: ${addressData.izgotovitel}<br />Страна: ${addressData.izgotovitelCountry}<br />Наименование: ${addressData.name}`;
            await addMarker(addressData.izgotovitelAddress, `Изготовитель ${addressData.name}`, addressData.name, izgInfo, true);
            var zaInfo = `<br />${addressData.il}<br />Адрес: ${addressData.zayavitelAddress}<br />Организация: ${addressData.zayavitel}<br />Страна: РОССИЯ<br />Наименование: ${addressData.name}`;
            await addMarker(addressData.zayavitelAddress, `Заявитель ${addressData.name}`, addressData.name, zaInfo, false);
        }
    } catch (e) {
        console.error(e);
        alert('Что-то пошло не так: ' + e);
    }
};

async function getAddresses(query) {
    return await queryBackend('getAddresses', {
        'name': query
    });
};

var queryBackend = async function (method, params) {
    const backendAddress = 'localhost';
    const protocol = 'http';
    let url = backendAddress;

    return new Promise((resolve, reject) => {
        let xhr = new XMLHttpRequest();
        xhr.timeout = 2000;
        let request = `${protocol}://${url}/${method}`;
        xhr.open('POST', request);
        xhr.onload = () => {
            let response = JSON.parse(xhr.responseText);
            resolve(response);
        };
        xhr.ontimeout = () => {
            reject('Ошибка сети');
        };
        xhr.onerror = () => {
            reject('Ошибка сети');
        };
        xhr.send(JSON.stringify(params));
    });
};

async function addMarker(address, header, title, info, isBlue) {
    // let point = await getOSMCoordinates(address);
    let point = await getYandexCoordinates(address);
    if (point == null) {
        console.error('Адрес не найден: ' + address);
        return;
    }
    point.header = header;
    point.info = info;
    drawMarker(point, title, isBlue);
}

async function getYandexCoordinates(address) {
    let geocode = encodeURIComponent(address);
    let apiKey = 'a9097011-1b82-425e-915b-92e1938a14dc';
    let request = `https://geocode-maps.yandex.ru/1.x/?format=json&apikey=${apiKey}&geocode=${geocode}`;
    let response = await queryBackend('getCoordinates', {
        'url': request
    });
    if (typeof response == 'text') {
        response = JSON.parse(response);
    }
    return parseYandexCoordinates(response);
};

function parseYandexCoordinates(response) {
    let fullData = response.response.GeoObjectCollection;
    if (fullData.featureMember.length == 0) {
        return null;
    }
    let pointString = fullData.featureMember[0].GeoObject.Point.pos;
    let stringCoords = pointString.split(' ');
    let result = {};
    result.x = parseFloat(stringCoords[1]);
    result.y = parseFloat(stringCoords[0]);
    return result;
}

async function getOSMCoordinates(address) {
    console.log('search address: ' + address);
    let addrItems = address.split(' ');
    address = addrItems[0] + ' ' + addrItems[1];
    let geocode = encodeURIComponent(address);
    let request = `https://nominatim.openstreetmap.org/search?format=json&q=${geocode}`;
    let response = await queryBackend('getCoordinates', {
        'url': request
    });
    response = JSON.parse(response);
    console.log(response);
    return parseOSMCoordinates(response);
};

function parseOSMCoordinates(response) {
    let fullData = response[0];
    console.log(fullData);
    let result = {};
    result.x = parseFloat(fullData.lat);
    result.y = parseFloat(fullData.lon);
    return result;
}

function drawMarker(point, title, isBlue) {
    let mark = new ymaps.Placemark([point.x, point.y], {
        balloonContent: point.info,
        balloonContentHeader: point.header,
        iconCaption: title
    }, {
        preset: isBlue ? 'islands#blueDotIcon' : 'islands#redDotIcon',
        iconCaptionMaxWidth: '150'
    });
    mapRef.geoObjects.add(mark);
};

function clearMarkers() {
    mapRef.geoObjects.removeAll();
};
