// Fix for missing window.location.origin in IE
if (!window.location.origin) {
  window.location.origin = window.location.protocol + "//" + window.location.hostname + (window.location.port ? ':' + window.location.port: '');
}

// Our convienience functions
window.Stencila = (function(){

	/**
	 * Get a cookie. Code from https://docs.djangoproject.com/en/1.9/ref/csrf/#ajax
	 * 
	 * @param  {[type]} name [description]
	 * @return {[type]}      [description]
	 */
	function cookie(name) {
		var cookieValue = null;
		if (document.cookie && document.cookie !== '') {
			var cookies = document.cookie.split(';');
			for (var i = 0; i < cookies.length; i++) {
				var cookieOne = jQuery.trim(cookies[i]);
				if (cookieOne.substring(0, name.length + 1) == (name + '=')) {
					cookieValue = decodeURIComponent(cookieOne.substring(name.length + 1));
					break;
				}
			}
		}
		return cookieValue;
	}

	function request(method, path, data){
		// Check that path is 
		// JSONify the data automatically
		if (typeof data != "string") {
			data = JSON.stringify(data);
		}
		return $.ajax({
			method: method,
			// Ensure that this request is going to the host to prevent
			// a cross domain request sending cookie (below) and
			// make path absolute, not relative.
			url: window.location.origin + '/' + path,
			data: data,
			// Type of request body
			contentType: 'application/json',
			beforeSend: function(request){
				// Ensure requesting to get JSON back
				request.setRequestHeader("Accept", "application/json");
				// Set CSRF token. See https://docs.djangoproject.com/en/1.9/ref/csrf/#ajax
				if (!/^(GET|HEAD|OPTIONS|TRACE)$/.test(method)) {
					request.setRequestHeader("X-CSRFToken", cookie('csrftoken'));
				}
			},
		}).fail(function(xhr, textStatus, errorThrown){
			console.error(arguments);
		});
	}

	function post(url, data){
		return request('POST', url, data);
	}

	function put(url, data){
		return request('PUT', url, data);
	}

	return {
		post: post,
		put: put
	};

})();
