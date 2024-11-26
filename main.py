# region imports
from AlgorithmImports import *
from universe import SectorETFUniverseSelectionModel
from portfolio import CointegratedVectorPortfolioConstructionModel
# endregion

class ETFPairsTrading(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2023, 3, 1)  # Set Start Date
        self.set_end_date(2024, 3, 1) 
        self.set_cash(1000000)  # Set Strategy Cash

        lookback = self.get_parameter("lookback", 60)   # lookback window on correlation & coinetgration
        threshold = self.get_parameter("threshold", 2)   # we want at least 2+% expected profit margin to cover fees
        
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE, AccountType.MARGIN)
        # This should be a intra-day strategy
        self.set_security_initializer(lambda security: security.set_margin_model(PatternDayTradingMarginModel()))
        
        self.universe_settings.resolution = Resolution.MINUTE
        self.universe_settings.data_normalization_mode = DataNormalizationMode.RAW
        self.set_universe_selection(SectorETFUniverseSelectionModel(self.universe_settings))

        # This alpha model helps to pick the most correlated pair
        # and emit signal when they have mispricing that stay active for a predicted period
        # https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/alpha/supported-models#09-Pearson-Correlation-Pairs-Trading-Model
        self.add_alpha(PearsonCorrelationPairsTradingAlphaModel(lookback, Resolution.DAILY, threshold=threshold))

        # We try to use cointegrating vector to decide the relative movement magnitude of the paired assets
        self.pcm = CointegratedVectorPortfolioConstructionModel(self, lookback, Resolution.DAILY)
        self.pcm.rebalance_portfolio_on_security_changes = False
        self.set_portfolio_construction(self.pcm)

        # Avoid catastrophic loss in portfolio level by pair trading strategy
        self.add_risk_management(MaximumDrawdownPercentPortfolio(0.08))

        self.set_warm_up(timedelta(90))

    def on_data(self, slice):
        if slice.splits or slice.dividends:
            self.pcm.handle_corporate_actions(self, slice)