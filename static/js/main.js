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
    alert('test click');
    $.post(URLS.requestPay, { money: 1 }, function(ticket) {
        wx.chooseWXPay({
            timestamp: ticket.timeStamp,
            nonceStr: ticket.nonceStr,
            package: ticket.package,
            signType: ticket.signType,
            paySign: ticket.paySign,
            success: function(res) {
                debug('success');
            },
            error: function(err) {
                debug('error');
            }
        });
    }, 'json');
}

function onCheckButtonClick() {
    alert('check');
}

function pay() {
    debug('abc');
    alert('wx');
    /*
    $.post(URLS.requestPay, { money: 1 }, function(ticket) {
        WeixinJSBridge.invoke(
            'getBrandWCPayRequest', 
            {
                "appId": "wx2421b1c4370ec43b",
            "timeStamp": "1395712654", 
            "nonceStr": "e61463f8efa94090b1f366cccfbbb444", //随机串     
            "package": "prepay_id=u802345jgfjsdfgsdg888",     
            "signType": "MD5",         //微信签名方式：     
            "paySign": "70EA570631E4BB79628FBCA90534C63FF7FADD89" //微信签名 
            },
            function(res){     
                if (res.err_msg == "get_brand_wcpay_request:ok" ) {
                    alert('fuck wx');
                }     // 
            }
        ); 
    });
    */
}
