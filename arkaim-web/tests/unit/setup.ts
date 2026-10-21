import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';

// Таймаут асинхронных утилит testing-library (waitFor / findBy*).
// По умолчанию 1000 мс — этого не хватает, когда 31 тестовый файл грузится
// параллельно на загруженной машине: тесты падали «мимо» (flaky), хотя логика
// была верной. 8000 мс совпадает с уже используемым в тестах таймаутом
// (findByText(..., { timeout: 8000 })) и не меняет проверяемые ожидания.
configure({ asyncUtilTimeout: 8000 });
