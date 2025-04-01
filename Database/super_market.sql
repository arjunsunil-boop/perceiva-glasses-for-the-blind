-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Apr 01, 2025 at 06:55 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `super_market`
--

-- --------------------------------------------------------

--
-- Table structure for table `items`
--

CREATE TABLE `items` (
  `item_id` int(11) NOT NULL,
  `item_name` varchar(100) NOT NULL,
  `category` varchar(50) DEFAULT NULL,
  `brand` varchar(50) DEFAULT NULL,
  `barcode` varchar(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `items`
--

INSERT INTO `items` (`item_id`, `item_name`, `category`, `brand`, `barcode`) VALUES
(1, 'toilet cleaner', 'Cleaning Agent', 'Harpic', '12345678901'),
(2, 'mineral water', 'Beverage', 'Aquafina', '98765432109'),
(3, 'cola', 'Beverage', 'Coco cola', '13579246801'),
(4, 'bingo', 'Snack', 'ITC', '11223344556'),
(5, 'noodles', 'Snack', 'Maggie', '99887766554'),
(6, 'oats', 'Cereal', 'Quaker', '666677778888'),
(7, 'peanut butter', 'Spread', 'Pintola', '999900001111'),
(8, 'wheat flour', 'Cereal', 'Aashirvaad', '555566667777'),
(9, 'horlicks', 'Nutritional Powder', 'Horlicks', '888899990000'),
(10, 'bathroom cleaner', 'Cleaning Agent', 'Harpic', '121212121212'),
(11, 'rice', 'Cereal', 'nirmal', '343434343434'),
(12, 'Soap', 'Cleaning', 'Vivel', '565656565656');

-- --------------------------------------------------------

--
-- Table structure for table `rack_positions`
--

CREATE TABLE `rack_positions` (
  `position_id` int(11) NOT NULL,
  `item_id` int(11) DEFAULT NULL,
  `row_from_top` int(11) NOT NULL,
  `position_in_row` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `rack_positions`
--

INSERT INTO `rack_positions` (`position_id`, `item_id`, `row_from_top`, `position_in_row`) VALUES
(1, 1, 3, 5),
(2, 2, 1, 1),
(3, 3, 1, 3),
(4, 4, 2, 1),
(5, 5, 3, 1),
(6, 6, 4, 2),
(7, 7, 4, 1),
(8, 8, 2, 3),
(9, 9, 3, 3),
(10, 10, 3, 4),
(11, 11, 5, 2),
(12, 12, 5, 3);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `items`
--
ALTER TABLE `items`
  ADD PRIMARY KEY (`item_id`);

--
-- Indexes for table `rack_positions`
--
ALTER TABLE `rack_positions`
  ADD PRIMARY KEY (`position_id`),
  ADD KEY `item_id` (`item_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `items`
--
ALTER TABLE `items`
  MODIFY `item_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT for table `rack_positions`
--
ALTER TABLE `rack_positions`
  MODIFY `position_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `rack_positions`
--
ALTER TABLE `rack_positions`
  ADD CONSTRAINT `rack_positions_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `items` (`item_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
