export default {
  // CalendarPage component translations
  calendarPage: {
    calendar: {
      allDay: 'Dia inteiro',
      day: 'Dia',
      list: 'Lista',
      month: 'Mês',
      noEvents: 'Sem eventos',
      today: 'Hoje',
      week: 'Semana',
    },
    categories: {
      cooperative: 'Condomínio',
      guestRoom: 'Quarto de hóspedes',
      plenary: 'Reunião geral, assembleia, etc.',
      reservation: 'Reserva',
    },
    errors: {
      calendarFeeds: 'Erro ao obter calendários.',
      general: 'Ocorreu um erro.',
      missingCredentials: 'Credenciais de acesso em falta.',
    },
    filter: {
      all: 'Todos',
      label: 'Filtrar',
    },
    views: {
      day: 'Dia',
      list: 'Lista',
      month: 'Mês',
      weekOverview: 'Semana — vista geral',
      weekTimeGrid: 'Semana — horários',
    },
    viewSelect: {
      label: 'Vista do calendário',
    },
  },

  // CreditAccountingPage component translations
  creditAccountingPage: {
    account: 'Conta',
    csvExport: 'Exportar CSV',
    csvExportFilename: 'Extrato_de_conta.csv',
    errors: {
      general: 'Ocorreu um erro.',
      invalidToken: 'Token inválido',
      missingCredentials: 'Credenciais de acesso em falta.',
    },
    filters: {
      allTransactions: 'Todas as transações',
      credits: 'Créditos',
      debits: 'Débitos',
    },
    messages: {
      displayed: 'apresentadas.',
      manyTransactions: 'Foram encontradas muitas transações. Apenas as mais recentes são',
      noTransactions:
        'Não foram encontradas transações. Ajuste os filtros, se necessário.',
    },
    paymentDialog: {
      accountLabel: 'Conta',
      autoAssignment: 'automaticamente associado à conta correta.',
      cancel: 'Cancelar',
      depositText: 'para depositar. Desta forma, a transferência pode ser',
      instructions:
        'Utilize a referência de pagamento abaixo para adicionar saldo à sua conta',
      qrSlip: 'Documento de pagamento QR (PDF)',
      title: 'Adicionar saldo',
    },
    search: 'Pesquisar',
    searchFilterLabel: 'Pesquisa, filtros e outras funções',
    settings: 'Definições',
    settingsDialog: {
      accountPrefix: 'Conta',
      cancel: 'Cancelar',
      emailNotification: 'Notificação por email,',
      emailTo: 'Email para',
      pinCode: 'Código PIN',
      save: 'Guardar',
      warning: 'ATENÇÃO: afeta todos os utilizadores da conta',
      whenBalanceBelow: 'quando o saldo for inferior a',
      withQrSlip: 'com documento QR quando o saldo descer abaixo deste limite.',
    },
    table: {
      amount: 'Montante',
      balance: 'Saldo',
      date: 'Data',
      description: 'Descrição',
      note: 'Nota',
    },
    timeRange: 'Período',
    title: 'Extrato de conta',
    type: 'Tipo',
  },

  // IndexPage component translations
  indexPage: {
    buttons: {
      calendar: 'Calendário',
      chat: 'Mensagens',
      cloud: 'Nuvem',
      depot8: 'Depot8',
      manual: 'Manual',
      repair: 'Comunicar avaria',
      reservation: 'Reserva',
    },
    errors: {
      general: 'Ocorreu um erro.',
      invalidToken: 'Token inválido',
      missingCredentials: 'Credenciais de acesso em falta.',
    },
    messages: {
      testMode: 'MODO DE TESTE — As alterações são enviadas apenas para um servidor de testes.',
    },
  },

  // LoginPage component translations
  loginPage: {
    backendError: {
      retry: 'Tentar novamente',
      title: 'Servidor indisponível',
    },
    checkingServer: 'A verificar ligação ao servidor...',
    forgotPassword: 'Esqueceu-se da palavra-passe?',
    loginButton: 'Entrar com {site}',
    loginError: 'Falha na autenticação. Tente novamente.',
    redirectNotice: 'Será redirecionado para a página segura de autenticação.',
    title: 'Entre com a sua conta {site}:',
  },

  // MainLayout component translations
  mainLayout: {
    appVersion: {
      label: 'Versão da aplicação',
    },
    navigation: {
      links: 'Ligações',
      settings: 'Definições',
    },
    user: {
      loggedInAs: 'Sessão iniciada como',
      logout: 'Terminar sessão',
      unknown: 'Desconhecido',
    },
  },

  // Page titles for SubpageLayout
  pageTitles: {
    calendar: 'Calendário',
    creditAccounting: 'Extrato de conta',
    repair: 'Comunicar avaria',
    reservation: 'Reserva',
  },

  // RepairPage component translations
  repairPage: {
    errorDialog: {
      message: 'Não foi possível enviar a comunicação.',
      ok: 'OK',
      reason: 'Motivo:',
      title: 'Erro',
    },
    errors: {
      general: 'Ocorreu um erro.',
      saveFailed: 'Erro ao guardar.',
    },
    form: {
      affectedArea: {
        label: 'Área/componente afetado',
      },
      affectedUnit: {
        label: 'Apartamento/divisão afetado',
        otherOption: 'Outro (indique no assunto)',
      },
      availability: {
        label: 'Disponibilidade',
        placeholder: 'Quando e como podemos contactá-lo?',
      },
      description: {
        label: 'Descrição da avaria',
        placeholder: 'Descreva a avaria ou o problema com o máximo de detalhe.',
      },
      images: {
        label: 'Adicionar fotografias',
      },
      requiredField: 'Campo obrigatório',
      subject: {
        label: 'Assunto',
        placeholder: 'Descreva brevemente o assunto',
      },
      submitButton: 'Enviar',
    },
    notifications: {
      invalidFile: 'Ficheiro inválido',
      maxImages: 'Pode adicionar até 5 imagens.',
    },
    reportFrom: 'Comunicação de:',
    successDialog: {
      message: 'A comunicação foi enviada com sucesso.',
      ok: 'OK',
      title: 'Obrigado!',
    },
  },

  // ReservationEditPage component translations
  reservationEditPage: {
    close: 'Fechar',
    confirmDialog: {
      cancelButton: 'Cancelar',
      costs: 'Custos:',
      date: 'Data:',
      dateFrom: 'De',
      dateTo: 'até',
      defaultCost: ' 0,00 €',
      reason: {
        label: 'Motivo da reserva',
        placeholder: 'Descrição breve',
        validation: 'Preencha este campo',
      },
      reserveButton: 'Reservar',
      room: 'Espaço:',
      title: 'Confirme a sua reserva:',
    },
    errorDialog: {
      message: 'Não foi possível concluir a reserva.',
      ok: 'OK',
      reason: 'Motivo:',
      title: 'Erro',
    },
    errors: {
      general: 'Ocorreu um erro.',
      invalidToken: 'Token inválido',
      missingCredentials: 'Credenciais de acesso em falta.',
      saveFailed: 'Erro ao guardar.',
    },
    from: 'De',
    links: 'Ligações',
    noPermission:
      'Não existem espaços disponíveis para reservar ou não tem as permissões necessárias.',
    notAvailable: 'Indisponível',
    note: 'Nota:',
    reserve: 'Reservar',
    title: 'Nova reserva',
    until: 'Até',
    whatToReserve: 'O que pretende reservar?',
  },

  // ReservationPage component translations
  reservationPage: {
    buttons: {
      edit: 'Editar',
    },
    cancelDialog: {
      cancelButton: 'Não, voltar',
      confirmButton: 'Sim, cancelar!',
      date: 'Data:',
      event: 'Evento:',
      explanation:
        'As reservas não podem ser alteradas. Cancele a reserva atual e crie uma nova.',
      question: 'Pretende cancelar definitivamente a seguinte reserva?',
      room: 'Espaço:',
      title: 'Cancelar reserva?',
    },
    emptyState:
      'Não tem reservas futuras. Para criar uma, utilize o botão + no canto inferior direito.',
    errorDialog: {
      message: 'Não foi possível cancelar a reserva.',
      ok: 'OK',
      reason: 'Motivo:',
      title: 'Erro',
    },
    errors: {
      general: 'Ocorreu um erro.',
      invalidToken: 'Token inválido',
      missingCredentials: 'Credenciais de acesso em falta.',
      saveFailed: 'Erro ao guardar.',
    },
    pastReservations: 'Reservas anteriores',
    status: {
      cancelled: 'CANCELADA',
    },
    title: 'As suas reservas',
  },
}
