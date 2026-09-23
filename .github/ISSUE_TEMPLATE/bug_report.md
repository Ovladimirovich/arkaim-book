name: Bug: _______

about: Сообщить о баге
title: '[Bug] '
labels: bug
body:
  - type: textarea
    attributes:
      label: Описание
      description: Что пошло не так?
    validations:
      required: true

  - type: textarea
    attributes:
      label: Как воспроизвести
      description: Пошаговая инструкция
    validations:
      required: true

  - type: textarea
    attributes:
      label: Ожидаемое поведение
      description: Что должно происходить?
    validations:
      required: true

  - type: input
    attributes:
      label: Окружение
      description: "OS, Python/TS версии, как запускали"
      placeholder: "Windows 11, Python 3.14, npm run dev"
    validations:
      required: false
