FROM nginx:alpine
COPY review/nginx.conf /etc/nginx/conf.d/default.conf
COPY review/index.html /usr/share/nginx/html/index.html
COPY review/admin.js /usr/share/nginx/html/admin.js
COPY review/style.css /usr/share/nginx/html/style.css
EXPOSE 80
