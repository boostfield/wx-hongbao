URLS = {
	getSign: "http://test.boostfield.com/api/jsapi/sign",
	requestPay: "http://test.boostfield.com/api/pay",
	getQRcode: "http://test.boostfield.com/api/share/qrcode",
	debug: "http://test.boostfield.com/api/debug",
	getLastIncome: "http://test.boostfield.com/api/income/last",
	getAgentAccount: "http://test.boostfield.com/api/agent/account",
	weixinQRcode: "https://mp.weixin.qq.com/cgi-bin/showqrcode",
	host: "http://test.boostfield.com"
};

function point2yuan(point) {
	return (point / 100).toString() + '元';
}

function newListContent(money, time) {
	var yuan = point2yuan(money);
	return '<div class="list-item"> \
<span class="fund">' + yuan + '</span>\
<span class="time">' + time + '</span>';
}

function debug(obj) {
	$.post(URLS.debug, obj);
}

function randString() {
	return Math.random().toString(36).substr(2);
}

var currentPage = 0;
var pageSize = 10;
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

	$('#imageQR').attr("onload", "generateShareImage()");
	$.get(URLS.getQRcode, function(rsp) {
		var qrUrl = URLS.host + '/qrcode/' + rsp.qrcode;
		$('#imageQR').attr("src", qrUrl);
	}, 'json');
}

function getLastIncome() {
	$.get(URLS.getLastIncome, function(rsp) {
		console.log(rsp);
		$("#btnGetRedPack").prop("disabled",false);
		if (rsp.msg == 'ok') {
			$('#rollResult').text(point2yuan(rsp.money));
			$('#modal').show();
		} else {

		}
	}, 'json');
}

$(document).ready(function() {
	$('#btnGetRedPack').click(function() {
		console.log("btnGetRedPack clicked");
		$(this).prop("disabled",true);
		$.ajax({												  
			url:URLS.requestPay,								  
			type: 'POST',										  
			data: JSON.stringify({ money: 1 }),					  
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
						$("#btnGetRedPack").prop("disabled",false);
					},											  
					success: function(ret) {					  
						console.log("pay success");				  
						
						setTimeout('getLastIncome()', 1000);
					}											  
				});												  
			},
			error: function(jqXHR, textStatus, errorThrown) {
				$("#btnGetRedPack").prop("disabled",false);
			}});
		

	});


	$(".tabbar-item").click(function() {
		$(this).addClass("active");
		$(".tabbar-item").not(this).each(function() {
			$(this).removeClass("active");
		});

		if($(this).hasClass("home")) {
			$('#page-home').addClass("active");
			$('#page-agent').removeClass("active");
			$('#page-share').removeClass("active");
		} else if($(this).hasClass("agent")) {
			$('#page-home').removeClass("active");
			$('#page-agent').addClass("active");
			$('#page-share').removeClass("active");
		} else {
			$('#page-home').removeClass("active");
			$('#page-agent').removeClass("active");
			$('#page-share').addClass("active");
		}
	});

	$('#modal').click(function() {
		$(this).hide();
	});

	$('.list-footer').click(function () {
		$('.list-footer').text("加载中...");
		$.get(URLS.getAgentAccount, { page: currentPage, pagesize: pageSize }, function(rsp) {
			if (rsp.ret == "SUCCESS") {
				console.log(rsp);
				$('.list-footer').text("加载更多");
				var list = $('div.list-content');
				$.each(rsp.bills, function(i, bill) {
					list.append(newListContent(bill.income, bill.time));
				});
				currentPage++;
				if(rsp.total_bill_num > currentPage*pageSize) {
					$('.list-footer').show();
				}else {
					$('.list-footer').hide();
				}
			}
		}, 'json');
	});

	$.get(URLS.getAgentAccount, { page: currentPage, pagesize: pageSize }, function(rsp) {

		if (rsp.ret == "SUCCESS") {
			console.log(rsp);
			$('.list-footer').text("加载更多");
			$('div.sended').text(point2yuan(rsp.total_income));
			$('div.unsend').text(point2yuan(rsp.shared_income));
			var list = $('div.list-content');
			$.each(rsp.bills, function(i, bill) {
				list.append(newListContent(bill.income, bill.time));
			});
			currentPage++;
			if(rsp.total_bill_num > currentPage*pageSize) {
				$('.list-footer').show();
			}else {
				$('.list-footer').hide();
			}
		}
	}, 'json');


	var canvas = document.getElementById("shareCanvas");
	canvas.width = screen.width;
	canvas.height = screen.height - 56;




});


function generateShareImage() {
	try {
		var canvas = document.getElementById("shareCanvas");
		canvas.width = screen.width;
		canvas.height = screen.height - 56;
		var imageBackground = document.getElementById("imageBackground");
		var imageBG = document.getElementById("imageBG");
		var imageQR = document.getElementById("imageQR");
		var imageResult = document.getElementById("imageResult");
		var canvasWidth = screen.width;
		var canvasHeight = screen.height - 56;
		var imageBGWidth = 347/375*canvasWidth;
		var imageBGHeight = 386/347*imageBGWidth;
		var imageQRWidth = 160/375*canvasWidth;

		var ctx = canvas.getContext("2d");
		ctx.drawImage(imageBackground, 0, 0, canvasWidth, canvasHeight);
		ctx.drawImage(imageBG, (canvasWidth - imageBGWidth) / 2, (canvasHeight - imageBGHeight) / 2, imageBGWidth, imageBGHeight);
		ctx.drawImage(imageQR,  (canvasWidth - imageQRWidth) / 2, (canvasHeight - imageQRWidth) / 2, imageQRWidth, imageQRWidth);

		var dataURL = canvas.toDataURL();
		imageResult.src = dataURL;
	}


	catch(err)
	{
		alert(err.message);
	}
}
