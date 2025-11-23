FROM node:18-alpine

# Устанавливаем только необходимые системные зависимости
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Копируем package.json отдельно для кэширования
COPY package.json package-lock.json* ./

# Устанавливаем зависимости с оптимизацией
RUN npm config set registry https://registry.npmjs.org/ \
    && npm install --production --no-optional --build-from-source \
    && npm cache clean --force

# Копируем исходный код
COPY . .

EXPOSE 8080

CMD ["npm", "start"]
