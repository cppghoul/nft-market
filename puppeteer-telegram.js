import puppeteer from 'puppeteer';

class PuppeteerTelegramAuth {
  constructor() {
    this.browser = null;
    this.page = null;
  }

  async init() {
    this.browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    this.page = await this.browser.newPage();
    await this.page.goto('https://web.telegram.org/');
  }

  async login(phone, code, password = null) {
    try {
      // Ввод номера телефона
      await this.page.waitForSelector('input[type="tel"]');
      await this.page.type('input[type="tel"]', phone);
      await this.page.click('button.btn-primary');

      // Ввод кода
      await this.page.waitForSelector('input[type="text"]', { timeout: 60000 });
      await this.page.type('input[type="text"]', code);
      await this.page.click('button.btn-primary');

      // Обработка пароля (если требуется)
      const passwordField = await this.page.$('input[type="password"]');
      if (passwordField && password) {
        await passwordField.type(password);
        await this.page.click('button.btn-primary');
      }

      // Получение данных сессии
      const sessionData = await this.page.evaluate(() => {
        return {
          authKey: window.localStorage.getItem('GramJs:apiId'),
          userId: window.localStorage.getItem('GramJs:userId')
        };
      });

      return { success: true, sessionData };

    } catch (error) {
      return { success: false, error: error.message };
    }
  }
}
