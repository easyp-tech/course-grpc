FROM nginx:1.25-alpine

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create log directory
RUN mkdir -p /var/log/nginx

# Expose ports
EXPOSE 80 5001 8080

# Use nginx daemon off mode for Docker
CMD ["nginx", "-g", "daemon off;"]
