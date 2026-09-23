name: Feature: _______

about: Предложить новую функцию
title: '[Feature] '
labels: enhancement
body:
  - type: input
    attributes:
      label: Название фичи
      description: Краткое название
    validations:
      required: true

  - type: textarea
    attributes:
      label: Описание
      description: Какую проблему решает фича? Почему нужна?
    validations:
      required: true

  - type: textarea
    attributes:
      label: Архитектурное влияние
      description: Какая часть архитектуры затрагивается? Pulse / World Engine / Knowledge Graph / UI?
    validations:
      required: true

  - type: textarea
    attributes:
      label: Voice-протокол
      description: Как фича вписывается в Voice-протокол? (Pulse → Voice → IdentityLayer.validate)
    validations:
      required: true
