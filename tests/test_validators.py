import unittest
import validators


class TestValidateCPF(unittest.TestCase):
    def test_valid_cpf(self):
        cpfs = ("01943533202", "15339928608", "38843691058", "54815838364")
        result = all(map(validators.validate_cpf, cpfs))

        self.assertTrue(result)

    def test_invalid_cpf(self):
        cpfs = ("1943533202", "12345678901", "11111111111", "548158a8364")
        result = any(map(validators.validate_cpf, cpfs))

        self.assertFalse(result)


class TestValidateCNPJ(unittest.TestCase):
    def test_valid_cnpj(self):
        cnpjs = ("89930840000167", "01327156000144", "27006197000122")
        result = all(map(validators.validate_cnpj, cnpjs))

        self.assertTrue(result)

    def test_invalid_cnpj(self):
        cnpjs = ("8993084000016", "11111111111111", "270061a7000122")
        result = any(map(validators.validate_cnpj, cnpjs))

        self.assertFalse(result)


class TestValidateEmail(unittest.TestCase):
    def test_valid_email(self):
        emails = (
            "user@localhost",
            "user.name@domain.com",
            "Test_Case@company.com.br",
            "domain-ip-address@250.202.100.191",
            "domain-ip-address123@250.202.100.191",
            "a.big_account-user~name!with^special#chars@the-test.io",
        )
        result = all(map(validators.validate_email, emails))

        self.assertTrue(result)

    def test_invalid_email(self):
        emails = (
            "",
            "missing-at-sign",
            "domain.less@",
            "@user.less",
            "invalid@test",
            "123@0.0.0.0",
            "invalidãccent@domain.com",
            "invalidáccênt@domain.com",
            "user name@domain.com",
            "hasasterisk*****@test.com",
            "hasasterisk.***@test.com",
            "j*smith@gmail.com",
            "********@gmail.com",
        )
        result = any(map(validators.validate_email, emails))

        self.assertFalse(result)


class TestValidateMobileNumber(unittest.TestCase):
    def test_valid_mobile_numbers(self):
        numbers = ("41987734440", "14988235412", "11987564321")
        result = all(map(validators.validate_mobile_number, numbers))

        self.assertTrue(result)

    def test_invalid_mobile_numbers(self):
        numbers = (
            "11111111111",
            "1198756432",
            "149882354126",
            "4198773444a",
            "+5541999128345",
        )
        result = any(map(validators.validate_mobile_number, numbers))

        self.assertFalse(result)


class TestValidatePix(unittest.TestCase):
    def test_valid_pix(self):
        values = (
            "01943533202",
            "89930840000167",
            "user.name@domain.com",
            "+5594969161652",
            "94969161652",
            "c3059309-a339-4585-9666-cc87749fd16b",
        )
        result = all(map(validators.validate_pix, values))

        self.assertTrue(result)

    def test_invalid_pix(self):
        values = (
            "0194353320",
            "8993084000016",
            "user.name",
            "+559496916165",
            "c3059309-a339-4585-9666-cc87749fd16",
        )
        result = any(map(validators.validate_pix, values))

        self.assertFalse(result)


class TestValidateName(unittest.TestCase):
    def test_valid_name(self):
        names = (
            "MariaSilva",
            "Maria da Silva",
            "Marina Silva",
            "Maria Silva",
            "Maria G. Silva",
            "Maria McDuffy",
            "Getúlio Dornelles Vargas",
            "Maria das Flores",
            "John Smith",
            "John D'Largy",
            "John Doe-Smith",
            "John Doe Smith",
            "Hector Sausage-Hausen",
            "Mathias d'Arras",
            "Martin Luther King Jr.",
            "Ai Wong",
            "Chao Chang",
            "Alzbeta Bara",
            "Marcos Assunção",
            "Maria da Silva e Silva",
            "Juscelino Kubitschek de Oliveira",
            "D'Artagnan",
        )
        for name in names:
            with self.subTest(msg=name):
                self.assertTrue(validators.validate_name(name))

    def test_invalid_name(self):
        names = (
            "0194353320",
            "8993084000016",
            "+559496916165",
            "0 Chao Chang",
            "0Chao Chang",
            " Chao Chang",
            "## Chao Chang",
            "$ Chao Chang",
        )

        for name in names:
            with self.subTest(msg=name):
                self.assertFalse(validators.validate_name(name))
