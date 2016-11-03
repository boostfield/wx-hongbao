URLS = {
	getSign: "http://test.boostfield.com/api/jsapi/sign",
    requestPay: "http://test.boostfield.com/api/pay",
    debug: "http://test.boostfield.com/api/debug"
};

function debug(obj) {
    $.post(URLS.debug, obj);
}

function randString() {
	return Math.random().toString(36).substr(2);
}

function onPageLoaded() {
	$.get(URLS.getSign, { url: window.location.href }, function(sign) {
        console.log(sign);
		wx.config({
			debug: true, // 开启调试模式,调用的所有api的返回值会在客户端alert出来，若要查看传入的参数，可以在pc端打开，参数信息会通过log打出，仅在pc端时才会打印。
			appId: sign.appid,
			timestamp: sign.timestamp,
			nonceStr: sign.noncestr,
			signature: sign.sign,
			jsApiList: ['checkJsApi', 'getBrandWCPayRequest', 'chooseWXPay'] // 必填，需要使用的JS接口列表，所有JS接口列表见附录2
		});

		wx.error(function(err) {
            alert(err);
            debug(err);
		});
	}, 'json');
}

function onButtonClick() {
    $.post(URLS.requestPay, { money: 1 }, function(ticket) {
        wx.chooseWXPay({
            timestamp: ticket.timeStamp,
            nonceStr: ticket.nonceStr,
            package: ticket.package,
            signType: ticket.signType,
            paySign: ticket.paySign,
            error: function(err) {
                debug('error');
            }
        });
    }, 'json');
}

function onCheckButtonClick() {
    alert('check');
}
