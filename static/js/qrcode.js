$(document).ready(function() {
	var ticket = getParameter('ticket');
	$("#qrcode").attr("src", 'https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=' + ticket);
});
