export const messages = {
  ru: {
    app: {
      language: 'Язык',
      russian: 'Русский',
      english: 'English'
    },
    common: {
      save: 'Сохранить',
      saveChanges: 'Сохранить изменения',
      cancel: 'Отмена',
      create: 'Создать',
      delete: 'Удалить',
      update: 'Обновить',
      choose: 'Выбрать',
      send: 'Отправить',
      search: 'Поиск',
      status: 'Статус',
      success: 'Успешно',
      selected: 'Выбрано',
      rows: 'строк'
    },
    validation: {
      tooShort: 'Слишком короткое значение',
      invalidEmail: 'Некорректный email',
      settingsUpdated: 'Настройки обновлены.',
      customerAdded: 'Новый пациент {name} добавлен'
    },
    login: {
      badge: 'Biologic LIMS',
      caption: 'Безопасный доступ',
      title: 'Вход в систему',
      description: 'Используйте учетные данные для доступа к панели управления и модулям лаборатории.',
      heroTitle: 'Все лабораторные процессы — в едином интерфейсе.',
      heroDescription: 'Единое рабочее пространство для сотрудников: мгновенный доступ к базе образцов, исследованиям, журналам исследований, уведомлениям и настройкам.',
      username: 'Логин',
      usernamePlaceholder: 'Введите логин',
      password: 'Пароль',
      passwordPlaceholder: 'Введите пароль',
      showPassword: 'Показать пароль',
      hidePassword: 'Скрыть пароль',
      remember: 'Запомнить меня',
      rememberHint: 'Оставаться в системе до 30 дней.',
      submit: 'Войти',
      demoTitle: 'Демонстрационный режим',
      demoDescription: 'Ознакомительный доступ к интерфейсу системы (dashboard). Позже здесь будет подключена реальная авторизация.',
      useAccount: 'Выбрать профиль',
      operatorTitle: 'Оператор',
      adminTitle: 'Администратор',
      successDescription: 'Успешная авторизация. Добро пожаловать, {username}!',
      validation: {
        usernameRequired: 'Введите логин.',
        usernameMin: 'Логин должен содержать не менее 3 символов.',
        usernameMax: 'Логин не может быть длиннее 64 символов.',
        usernameFormat: 'Используйте только буквы, цифры, дефисы и нижние подчёркивания.',
        passwordRequired: 'Введите пароль.',
        passwordMin: 'Пароль должен быть не короче 8 символов.',
        passwordMax: 'Пароль не может быть длиннее 128 символов.'
      }
    },
    nav: {
      home: 'Главная',
      inbox: 'Входящие',
      customers: 'Пациенты',
      requests: 'Заявки',
      requestsAll: 'Все заявки',
      requestsNew: 'Новая заявка',
      requestsArchive: 'Архив',
      samples: 'Образцы',
      samplesJournal: 'Журнал образцов',
      samplesMovement: 'Движение образцов',
      results: 'Результаты',
      resultsInput: 'Ввод результатов',
      resultsVerification: 'Верификация',
      resultsReports: 'Отчёты',
      dictionaries: 'Справочники',
      dictionariesAnalyses: 'Виды анализов',
      dictionariesObjects: 'Объекты исследований',
      dictionariesReferences: 'Нормы и референсы',
      dictionariesOrganizations: 'Организации / клиенты',
      settings: 'Настройки',
      settingsUsers: 'Пользователи и роли',
      settingsBranches: 'Филиалы и подразделения',
      settingsSystem: 'Параметры системы',
      documentation: 'Документация'
    },
    layout: {
      goTo: 'Перейти',
      quickActions: 'Быстрые действия',
      createOrder: 'Создать новый заказ',
      importData: 'Импортировать данные',
      exportData: 'Экспортировать данные',
      cookieTitle: 'Мы используем файлы cookie для улучшения вашего опыта на нашем сайте.',
      accept: 'Принять',
      decline: 'Отказаться'
    },
    userMenu: {
      palette: 'Палитра',
      primary: 'Основной цвет',
      neutral: 'Нейтральный цвет',
      theme: 'Тема',
      light: 'Светлая',
      dark: 'Тёмная',
      logout: 'Выйти',
      logoutTitle: 'Успешно',
      logoutDescription: 'Вы вышли из аккаунта'
    },
    dashboard: {
      notifications: 'Уведомления',
      quickActions: 'Быстрые действия',
      newMail: 'Новое письмо',
      newCustomer: 'Новый пациент',
      stats: {
        patients: 'Пациенты',
        analyses: 'Анализы выполнено',
        critical: 'Критических результатов',
        averageTime: 'Среднее время (мин)'
      },
      chart: {
        title: 'Образцы за период',
        defective: 'Бракованных',
        totalSamples: 'Всего образцов',
        total: 'Всего'
      },
      periods: {
        daily: 'По дням',
        weekly: 'По неделям',
        monthly: 'По месяцам'
      },
      ranges: {
        last7Days: 'Последние 7 дней',
        last14Days: 'Последние 14 дней',
        last30Days: 'Последние 30 дней',
        last3Months: 'Последние 3 месяца',
        last6Months: 'Последние 6 месяцев',
        lastYear: 'Последний год',
        pickDate: 'Выберите период'
      },
      sales: {
        id: 'ID',
        date: 'Дата',
        status: 'Статус',
        email: 'Email',
        amount: 'Сумма',
        paid: 'Оплачено',
        failed: 'Ошибка',
        refunded: 'Возврат'
      }
    },
    inbox: {
      title: 'Входящие',
      systemTitle: 'Системное сообщение',
      all: 'Все',
      unread: 'Непрочитанные',
      empty: 'Сообщений нет',
      noUnread: 'Непрочитанных уведомлений нет',
      open: 'Открыть',
      read: 'Прочитать',
      archive: 'Архивировать',
      reply: 'Ответить',
      markUnread: 'Отметить как непрочитанное',
      markImportant: 'Отметить как важное',
      starThread: 'В избранное',
      muteThread: 'Отключить уведомления',
      replyTo: 'Ответ для {name} ({email})',
      writeReply: 'Напишите ответ...',
      attachFile: 'Прикрепить файл',
      saveDraft: 'Черновик',
      send: 'Отправить',
      sentTitle: 'Письмо отправлено',
      sentDescription: 'Ваше письмо успешно отправлено'
    },
    notifications: {
      title: 'Уведомления'
    },
    customers: {
      title: 'Пациенты',
      actions: 'Действия',
      copyId: 'Копировать ID',
      copiedTitle: 'Скопировано',
      copiedDescription: 'ID пациента скопирован',
      viewCard: 'Просмотр карты',
      analysisHistory: 'История анализов',
      deletePatient: 'Удалить пациента',
      deletedTitle: 'Пациент удалён',
      allStatuses: 'Все',
      subscribed: 'Подписан',
      unsubscribed: 'Отписан',
      bounced: 'Отклонён',
      columns: 'Столбцы',
      selectedRows: '{selected} из {total} строк выбрано',
      selectAll: 'Выбрать все',
      selectRow: 'Выбрать строку',
      fields: {
        id: 'ID',
        name: 'Пациент',
        email: 'Email',
        location: 'Местоположение',
        status: 'Статус'
      },
      create: {
        title: 'Новый пациент',
        description: 'Добавьте нового пациента в систему',
        button: 'Новый пациент',
        name: 'Имя',
        email: 'Email'
      },
      deleteDialog: {
        title: 'Удалить записи ({count})',
        description: 'Вы уверены? Это действие нельзя отменить.'
      }
    },
    settings: {
      title: 'Настройки',
      general: 'Общие',
      members: 'Участники',
      notifications: 'Уведомления',
      security: 'Безопасность',
      documentation: 'Документация',
      profile: {
        title: 'Профиль',
        description: 'Эти данные будут отображаться публично.',
        name: 'Имя',
        nameDescription: 'Будет использоваться в квитанциях, счетах и другой коммуникации.',
        email: 'Email',
        emailDescription: 'Используется для входа, писем и обновлений продукта.',
        username: 'Имя пользователя',
        usernameDescription: 'Ваш уникальный логин и адрес профиля.',
        avatar: 'Аватар',
        avatarDescription: 'JPG, GIF или PNG. Максимум 1 МБ.',
        bio: 'О себе',
        bioDescription: 'Краткое описание профиля. Ссылки будут активными.'
      },
      membersPage: {
        title: 'Участники',
        description: 'Приглашайте новых участников по адресу электронной почты.',
        invite: 'Пригласить',
        search: 'Поиск участников'
      },
      memberList: {
        edit: 'Изменить участника',
        remove: 'Удалить участника',
        member: 'Участник',
        owner: 'Владелец'
      },
      notificationsPage: {
        channelsTitle: 'Каналы уведомлений',
        channelsDescription: 'Куда мы можем отправлять уведомления?',
        email: 'Email',
        emailDescription: 'Получать ежедневную сводку по почте.',
        desktop: 'Рабочий стол',
        desktopDescription: 'Получать уведомления на рабочем столе.',
        updatesTitle: 'Обновления аккаунта',
        updatesDescription: 'Получайте обновления о Nuxt UI.',
        weeklyDigest: 'Еженедельная сводка',
        weeklyDigestDescription: 'Получать еженедельную сводку новостей.',
        productUpdates: 'Обновления продукта',
        productUpdatesDescription: 'Получать ежемесячное письмо со всеми новыми возможностями.',
        importantUpdates: 'Важные обновления',
        importantUpdatesDescription: 'Получать письма о важных обновлениях: безопасность, обслуживание и другое.'
      },
      securityPage: {
        passwordTitle: 'Пароль',
        passwordDescription: 'Подтвердите текущий пароль перед установкой нового.',
        currentPassword: 'Текущий пароль',
        newPassword: 'Новый пароль',
        deleteAccount: 'Удалить аккаунт',
        accountTitle: 'Аккаунт',
        accountDescription: 'Если вы больше не хотите пользоваться сервисом, можно удалить аккаунт здесь. Это действие необратимо. Все связанные данные будут удалены навсегда.',
        minLength: 'Минимум 8 символов',
        passwordsDifferent: 'Пароли должны отличаться'
      }
    }
  },
  en: {
    app: {
      language: 'Language',
      russian: 'Russian',
      english: 'English'
    },
    common: {
      save: 'Save',
      saveChanges: 'Save changes',
      cancel: 'Cancel',
      create: 'Create',
      delete: 'Delete',
      update: 'Update',
      choose: 'Choose',
      send: 'Send',
      search: 'Search',
      status: 'Status',
      success: 'Success',
      selected: 'Selected',
      rows: 'rows'
    },
    validation: {
      tooShort: 'Too short',
      invalidEmail: 'Invalid email',
      settingsUpdated: 'Your settings have been updated.',
      customerAdded: 'New patient {name} added'
    },
    login: {
      badge: 'Biologic LIMS',
      caption: 'Secure sign in',
      title: 'Sign in to your workspace',
      description: 'Use your corporate account to open the operator dashboard and internal laboratory modules.',
      heroTitle: 'Laboratory operations in one interface.',
      heroDescription: 'A Nuxt UI sign-in screen for internal users with fast access to notifications, patients, settings, and process journals.',
      username: 'Username',
      usernameDescription: 'Enter your corporate username.',
      usernamePlaceholder: 'operator',
      password: 'Password',
      passwordDescription: 'Minimum 8 characters. Validation is handled by the form schema.',
      passwordPlaceholder: 'Enter your password',
      showPassword: 'Show password',
      hidePassword: 'Hide password',
      remember: 'Remember me',
      rememberHint: 'You will be logged in for 30 days.',
      forgotPassword: 'Forgot password?',
      submit: 'Sign in',
      demoTitle: 'Demo sign in',
      demoDescription: 'The form currently performs a client-side redirect to the dashboard. You can wire a real auth API here later.',
      useAccount: 'Use account',
      operatorTitle: 'Operator',
      adminTitle: 'Administrator',
      successDescription: 'Signed in as {username}',
      validation: {
        usernameRequired: 'Enter your username.',
        usernameMin: 'Username must be at least 3 characters.',
        usernameMax: 'Username must not exceed 64 characters.',
        usernameFormat: 'Only letters, numbers, dots, dashes, and underscores are allowed.',
        passwordRequired: 'Enter your password.',
        passwordMin: 'Password must be at least 8 characters.',
        passwordMax: 'Password must not exceed 128 characters.'
      }
    },
    nav: {
      home: 'Home',
      inbox: 'Inbox',
      customers: 'Patients',
      requests: 'Requests',
      requestsAll: 'All requests',
      requestsNew: 'New request',
      requestsArchive: 'Archive',
      samples: 'Samples',
      samplesJournal: 'Sample journal',
      samplesMovement: 'Sample movement',
      results: 'Results',
      resultsInput: 'Results entry',
      resultsVerification: 'Verification',
      resultsReports: 'Reports',
      dictionaries: 'Reference data',
      dictionariesAnalyses: 'Analysis types',
      dictionariesObjects: 'Research objects',
      dictionariesReferences: 'Norms and references',
      dictionariesOrganizations: 'Organizations / clients',
      settings: 'Settings',
      settingsUsers: 'Users and roles',
      settingsBranches: 'Branches and departments',
      settingsSystem: 'System settings',
      documentation: 'Documentation'
    },
    layout: {
      goTo: 'Go to',
      quickActions: 'Quick actions',
      createOrder: 'Create new order',
      importData: 'Import data',
      exportData: 'Export data',
      cookieTitle: 'We use cookies to improve your experience on our website.',
      accept: 'Accept',
      decline: 'Decline'
    },
    userMenu: {
      palette: 'Palette',
      primary: 'Primary color',
      neutral: 'Neutral color',
      theme: 'Theme',
      light: 'Light',
      dark: 'Dark',
      logout: 'Log out',
      logoutTitle: 'Success',
      logoutDescription: 'You have been signed out'
    },
    dashboard: {
      notifications: 'Notifications',
      quickActions: 'Quick actions',
      newMail: 'New mail',
      newCustomer: 'New patient',
      stats: {
        patients: 'Patients',
        analyses: 'Completed analyses',
        critical: 'Critical results',
        averageTime: 'Average time (min)'
      },
      chart: {
        title: 'Samples over period',
        defective: 'Defective',
        totalSamples: 'Total samples',
        total: 'Total'
      },
      periods: {
        daily: 'Daily',
        weekly: 'Weekly',
        monthly: 'Monthly'
      },
      ranges: {
        last7Days: 'Last 7 days',
        last14Days: 'Last 14 days',
        last30Days: 'Last 30 days',
        last3Months: 'Last 3 months',
        last6Months: 'Last 6 months',
        lastYear: 'Last year',
        pickDate: 'Pick a date range'
      },
      sales: {
        id: 'ID',
        date: 'Date',
        status: 'Status',
        email: 'Email',
        amount: 'Amount',
        paid: 'Paid',
        failed: 'Failed',
        refunded: 'Refunded'
      }
    },
    inbox: {
      title: 'Inbox',
      systemTitle: 'System message',
      all: 'All',
      unread: 'Unread',
      empty: 'No messages',
      noUnread: 'No unread notifications',
      open: 'Open',
      read: 'Read',
      archive: 'Archive',
      reply: 'Reply',
      markUnread: 'Mark as unread',
      markImportant: 'Mark as important',
      starThread: 'Star thread',
      muteThread: 'Mute thread',
      replyTo: 'Reply to {name} ({email})',
      writeReply: 'Write your reply...',
      attachFile: 'Attach file',
      saveDraft: 'Save draft',
      send: 'Send',
      sentTitle: 'Email sent',
      sentDescription: 'Your email has been sent successfully'
    },
    notifications: {
      title: 'Notifications'
    },
    customers: {
      title: 'Patients',
      actions: 'Actions',
      copyId: 'Copy ID',
      copiedTitle: 'Copied',
      copiedDescription: 'Patient ID copied',
      viewCard: 'View card',
      analysisHistory: 'Analysis history',
      deletePatient: 'Delete patient',
      deletedTitle: 'Patient deleted',
      allStatuses: 'All',
      subscribed: 'Subscribed',
      unsubscribed: 'Unsubscribed',
      bounced: 'Bounced',
      columns: 'Columns',
      selectedRows: '{selected} of {total} rows selected',
      selectAll: 'Select all',
      selectRow: 'Select row',
      fields: {
        id: 'ID',
        name: 'Patient',
        email: 'Email',
        location: 'Location',
        status: 'Status'
      },
      create: {
        title: 'New patient',
        description: 'Add a new patient to the system',
        button: 'New patient',
        name: 'Name',
        email: 'Email'
      },
      deleteDialog: {
        title: 'Delete entries ({count})',
        description: 'Are you sure? This action cannot be undone.'
      }
    },
    settings: {
      title: 'Settings',
      general: 'General',
      members: 'Members',
      notifications: 'Notifications',
      security: 'Security',
      documentation: 'Documentation',
      profile: {
        title: 'Profile',
        description: 'This information will be displayed publicly.',
        name: 'Name',
        nameDescription: 'Will appear on receipts, invoices, and other communication.',
        email: 'Email',
        emailDescription: 'Used to sign in, for email receipts and product updates.',
        username: 'Username',
        usernameDescription: 'Your unique login and profile URL.',
        avatar: 'Avatar',
        avatarDescription: 'JPG, GIF or PNG. 1MB max.',
        bio: 'Bio',
        bioDescription: 'Brief description for your profile. URLs are hyperlinked.'
      },
      membersPage: {
        title: 'Members',
        description: 'Invite new members by email address.',
        invite: 'Invite people',
        search: 'Search members'
      },
      memberList: {
        edit: 'Edit member',
        remove: 'Remove member',
        member: 'Member',
        owner: 'Owner'
      },
      notificationsPage: {
        channelsTitle: 'Notification channels',
        channelsDescription: 'Where can we notify you?',
        email: 'Email',
        emailDescription: 'Receive a daily email digest.',
        desktop: 'Desktop',
        desktopDescription: 'Receive desktop notifications.',
        updatesTitle: 'Account updates',
        updatesDescription: 'Receive updates about Nuxt UI.',
        weeklyDigest: 'Weekly digest',
        weeklyDigestDescription: 'Receive a weekly digest of news.',
        productUpdates: 'Product updates',
        productUpdatesDescription: 'Receive a monthly email with all new features and updates.',
        importantUpdates: 'Important updates',
        importantUpdatesDescription: 'Receive emails about important updates like security fixes, maintenance, and more.'
      },
      securityPage: {
        passwordTitle: 'Password',
        passwordDescription: 'Confirm your current password before setting a new one.',
        currentPassword: 'Current password',
        newPassword: 'New password',
        deleteAccount: 'Delete account',
        accountTitle: 'Account',
        accountDescription: 'No longer want to use our service? You can delete your account here. This action is not reversible. All information related to this account will be deleted permanently.',
        minLength: 'Must be at least 8 characters',
        passwordsDifferent: 'Passwords must be different'
      }
    }
  }
} as const

export type MessageSchema = typeof messages.en
