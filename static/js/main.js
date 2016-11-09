URLS = {
	getSign: "http://test.boostfield.com/api/jsapi/sign",
    requestPay: "http://test.boostfield.com/api/pay",
	getQRcode: "http://test.boostfield.com/api/share/qrcode",
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
            //debug: true, // 开启调试模式,调用的所有api的返回值会在客户端alert出来，若要查看传入的参数，可以在pc端打开，参数信息会通过log打出，仅在pc端时才会打印。
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

$(document).ready(function() {
	$("#btn-get-qrcode").click(function() {
		$.get(URLS.getQRcode, function(ticket) {
			if (ticket.ret != 'SUCCESS') {
				console.log(ticket.msg);
				return;
			}
			window.location.href = "qrcode.html?ticket=" + encodeURI(ticket.ticket);
		}, 'json');
	});
});

function onButtonClick() {
	$.ajax({
		url:URLS.requestPay,
		type: 'POST',
		data: JSON.stringify({ money: 500 }),
		contentType: 'application/json; charset=utf-8',
		dataType: 'json',
		success: function(ticket) {
			wx.chooseWXPay({
				timestamp: ticket.timeStamp,
				nonceStr: ticket.nonceStr,
				package: ticket.package,
				signType: ticket.signType,
				paySign: ticket.paySign,
				error: function(err) {
					debug('error');
				}
			})
		}});
}

function onCheckButtonClick() {
	alert('check');
}
