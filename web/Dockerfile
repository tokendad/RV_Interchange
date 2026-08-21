FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY app.js /usr/share/nginx/html/app.js
COPY chrome.js /usr/share/nginx/html/chrome.js
COPY url-state.js /usr/share/nginx/html/url-state.js
COPY coverage.html /usr/share/nginx/html/coverage.html
COPY coverage.js /usr/share/nginx/html/coverage.js
COPY how-it-works.html /usr/share/nginx/html/how-it-works.html
COPY contact.html /usr/share/nginx/html/contact.html
COPY page-init.js /usr/share/nginx/html/page-init.js
COPY api-client.js /usr/share/nginx/html/api-client.js
COPY results.js /usr/share/nginx/html/results.js
COPY detail.js /usr/share/nginx/html/detail.js
COPY discontinued.js /usr/share/nginx/html/discontinued.js
COPY style.css /usr/share/nginx/html/style.css
COPY assets /usr/share/nginx/html/assets
EXPOSE 80
