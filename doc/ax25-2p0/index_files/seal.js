var _____WB$wombat$assign$function_____ = function(name) {return (self._wb_wombat && self._wb_wombat.local_init && self._wb_wombat.local_init(name)) || self[name]; };
if (!self.__WB_pmw) { self.__WB_pmw = function(obj) { this.__WB_source = obj; return this; } }
{
  let window = _____WB$wombat$assign$function_____("window");
  let self = _____WB$wombat$assign$function_____("self");
  let document = _____WB$wombat$assign$function_____("document");
  let location = _____WB$wombat$assign$function_____("location");
  let top = _____WB$wombat$assign$function_____("top");
  let parent = _____WB$wombat$assign$function_____("parent");
  let frames = _____WB$wombat$assign$function_____("frames");
  let opener = _____WB$wombat$assign$function_____("opener");

// (c) 2006. Authorize.Net is a registered trademark of Lightbridge, Inc.
var ANSVerificationURL = "http://web.archive.org/web/20190831185324/https://verify.authorize.net/anetseal/";  // String must start with "//" and end with "/"
var AuthorizeNetSeal = 
{
	verification_parameters: "",
	id_parameter_name:       "pid",
	url_parameter_name:      "rurl",
	seal_image_file:         (ANSVerificationURL + "images/secure90x72.gif"),
	seal_width:              "90",
	seal_height:             "72",
	seal_alt_text:           "Authorize.Net Merchant - Click to Verify",
	display_url:             "http://web.archive.org/web/20190831185324/http://www.authorize.net/",
	text_color:              "black",
	text_size:               "9px",
	line_spacing:            "10px",
	new_window_height:       "430",
	new_window_width:        "600",
	current_url:             "",
	display_location:        true,
	no_click:                false,
	debug:                   false
};

document.writeln( '<style type="text/css">' );
document.writeln( 'div.AuthorizeNetSeal{text-align:center;margin:0;padding:0;width:' + AuthorizeNetSeal.seal_width + 'px;font:normal ' + AuthorizeNetSeal.text_size + ' arial,helvetica,san-serif;line-height:' + AuthorizeNetSeal.line_spacing + ';}' );
document.writeln( 'div.AuthorizeNetSeal a{text-decoration:none;color:' + AuthorizeNetSeal.text_color + ';}' );
document.writeln( 'div.AuthorizeNetSeal a:visited{color:' + AuthorizeNetSeal.text_color + ';}' );
document.writeln( 'div.AuthorizeNetSeal a:active{color:' + AuthorizeNetSeal.text_color + ';}' );
document.writeln( 'div.AuthorizeNetSeal a:hover{text-decoration:underline;color:' + AuthorizeNetSeal.text_color + ';}' );
document.writeln( 'div.AuthorizeNetSeal a img{border:0px;margin:0px;text-decoration:none;}' );
document.writeln( '</style>' );

if( window.ANS_customer_id )
{
	AuthorizeNetSeal.verification_parameters = '?' + AuthorizeNetSeal.id_parameter_name + '=' + escape( ANS_customer_id );
	if( window.location.href )
	{
		AuthorizeNetSeal.current_url = window.location.href;
	}
	else if( document.URL )
	{
		AuthorizeNetSeal.current_url = document.URL;
	}

	if( AuthorizeNetSeal.current_url )
	{
		AuthorizeNetSeal.verification_parameters += '&' + AuthorizeNetSeal.url_parameter_name + '=' + escape( AuthorizeNetSeal.current_url );
	}

	if( !AuthorizeNetSeal.no_click )
	{
		document.write( '<a ' );
		document.write( 'href="' + ANSVerificationURL  + AuthorizeNetSeal.verification_parameters + '" ' );
		if( !AuthorizeNetSeal.debug )
		{
			document.write( 'onMouseOver="window.status=\'' + AuthorizeNetSeal.display_url + '\'; return true;" ' );
			document.write( 'onMouseOut="window.status=\'\'; return true;" ' );
			document.write( 'onClick="window.open(\'' + ANSVerificationURL + AuthorizeNetSeal.verification_parameters + '\',\'AuthorizeNetVerification\',\'' );
			document.write( 'width=' + AuthorizeNetSeal.new_window_width );
			document.write( ',height=' + AuthorizeNetSeal.new_window_height );
			document.write( ',dependent=yes,resizable=yes,scrollbars=yes' );
			document.write( ',menubar=no,toolbar=no,status=no,directories=no' );
			if( AuthorizeNetSeal.display_location )
			{
				document.write( ',location=yes' );
			}
			document.write( '\'); return false;" ' );
		}
		document.write( 'target="_blank"' );
		document.writeln( '>' );
	}

	document.writeln( '<img src="' + AuthorizeNetSeal.seal_image_file + '" width="' + AuthorizeNetSeal.seal_width + '" height="' + AuthorizeNetSeal.seal_height + '" border="0" alt="' + AuthorizeNetSeal.seal_alt_text + '">' );

	if( !AuthorizeNetSeal.no_click )
	{
		document.writeln( '</a>' );
	}
}


}
/*
     FILE ARCHIVED ON 18:53:24 Aug 31, 2019 AND RETRIEVED FROM THE
     INTERNET ARCHIVE ON 06:36:00 Oct 23, 2023.
     JAVASCRIPT APPENDED BY WAYBACK MACHINE, COPYRIGHT INTERNET ARCHIVE.

     ALL OTHER CONTENT MAY ALSO BE PROTECTED BY COPYRIGHT (17 U.S.C.
     SECTION 108(a)(3)).
*/
/*
playback timings (ms):
  captures_list: 1475.342
  exclusion.robots: 0.121
  exclusion.robots.policy: 0.109
  cdx.remote: 0.082
  esindex: 0.01
  LoadShardBlock: 132.682 (4)
  PetaboxLoader3.datanode: 100.818 (5)
  load_resource: 59.75
  PetaboxLoader3.resolve: 43.32
*/